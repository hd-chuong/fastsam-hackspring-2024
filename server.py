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
        
    def generate_binary_mask_(self, link):
        image = cv2.imread(link)      
        height, width = image.shape[0], image.shape[1]
        
        # TODO: might need to save the image locally as 
        # later the base64 might be received instead of the image link.
        model = Model.STATIC_MODEL_X(link,
                                                  device='cpu',
                                                  retina_masks=True,
                                                  imgsz=1024,
                                                  conf=0.4,
                                                  iou=0.9)
        prompt_process = FastSAMPrompt(link,
                                       model,
                                       device='cpu')

        print("LOG - calculate annotation")
        ann = prompt_process.point_prompt(points=[[int(width/2),int(height/2)]], pointlabel=[1])
        binary_mask = np.where(ann > 0.5, 1, 0)
        return binary_mask[0]

    def extract_object_(self, image, binary_mask):
        object_only = image * binary_mask[..., np.newaxis]
        return np.dstack((object_only, binary_mask*255))
    
    def draw_boundary_(self, image, binary_mask):
        sihoutte = np.array(np.dstack((binary_mask * 255, binary_mask * 255,  binary_mask* 255)), dtype=np.uint8)
        gray = cv2.cvtColor(sihoutte, cv2.COLOR_BGR2GRAY) 
        
        # Find Canny edges 
        edged = cv2.Canny(gray, 30, 200) 
        cv2.waitKey(0) 
        
        # Finding Contours 
        # Use a copy of the image e.g. edged.copy() 
        # since findContours alters the image 
        contours, hierarchy = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE) 
        GREY_RGB_CODE = (100, 100, 100)
        image_with_contours = cv2.drawContours(image, contours, -1, GREY_RGB_CODE, 1)
        
        cv2.imwrite("../output/mask.png", image)
        return sihoutte 

    def infer(self, link):
        image = cv2.imread(link)      
        height, width = image.shape[0], image.shape[1]
        
        # generate binary mask
        print("LOG - calculate the binary mask:")
        binary_mask = self.generate_binary_mask_(link)
        
        # generate image with the extracted object
        print("LOG - generate new image:")
        image_with_transparent_background = self.extract_object_(image, binary_mask)
        
        # generate the boundary
        self.draw_boundary_(image, binary_mask)

        # TODO: might need to return the base64 data back
        print("LOG - save image")
        return cv2.imwrite("../output/output.png", image_with_transparent_background)


model = Model()
app = FastAPI()


@app.post("/ping")
async def test_ping(req: Request) -> Response:
    base64 = req.base64
    return Response(text=base64)


@app.post("/sticker")
async def generate_sticker(req: Request) -> Response:
    base64 = req.base64
    link = req.link 
    return Response(text="true" if model.infer(link) == True else "false")
