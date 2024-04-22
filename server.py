from fastsam import FastSAM, FastSAMPrompt
import cv2
from fastapi import FastAPI
from pydantic import BaseModel
import numpy as np


class Request(BaseModel):
    base64: str
    link: str

class Response(BaseModel):
    text: str


class Model:
    # FastSAM x model: 138MB
    STATIC_MODEL_X = FastSAM('FastSAM-x.pt')

    def __init__(self):
        self.__dump_temp = 'dump.png'
        

    def infer(self, link):
        image = cv2.cvtColor(cv2.imread(link),
                                    cv2.COLOR_BGR2RGB)
        
        # TODO: might need to save the image locally as 
        # later the base64 might be received instead of the image link.
        everything_results = Model.STATIC_MODEL_X(link,
                                                  device='cpu',
                                                  retina_masks=True,
                                                  imgsz=1024,
                                                  conf=0.4,
                                                  iou=0.9)
        prompt_process = FastSAMPrompt(link,
                                       everything_results,
                                       device='cpu')

        # Temporarily use segment everything prompt
        print("LOG - calculate annotation")
        ann = prompt_process.everything_prompt()

        binary_mask = np.where(ann > 0.5, 1, 0)
        white_background = np.ones_like(image) * 255

        print("LOG - generate new image")
        new_image = white_background * (1 - binary_mask[0][
            ..., np.newaxis]) + image * binary_mask[0][..., np.newaxis]

        # TODO: might need to return the base64 data back
        print("LOG - save segmentation data")
        return cv2.imwrite("../output/output.jpeg", new_image)


model = Model()
app = FastAPI()


@app.post("/ping")
async def test_ping(req: Request) -> Response:
    base64 = req.base64
    return Response(text=base64)


@app.post("/sticker")
async def generate_sticker(req: Request) -> Response:
    base64 = req.base64
    return Response(text="true" if model.infer(base64) == True else "false")

