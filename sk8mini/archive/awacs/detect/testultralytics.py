pip install ultralytics
!pip install roboflow


from googgle.colab import files
from ultralytics import YOLO
from roboflow import RoboFlow


import os
import random
import supervision as sv
import cv2
import yaml # a configuraion file similar to XML, SGML, JSON, CFG, etc.


model = YOLO('yolov8n-obb.pt')

rf = Roboflow(api_key="BHXttSz26bnlcjdm2357")
project = rf.workspace("voyc").project("sk8mini")
dataset = project.version(1).download("yolov8-obb")


results = model.train(data=f'{dataset.location}/data.yaml', epochs=100, imgsz=640)


model = YOLO('runs/obb/train2/weights/best.pt')


random_file = random.choice(os.listdir(f"{dataset.location}/test/images"))
file_name = os.path.join(f"{dataset.location}/test/images", random_file)

results = model(file_name)


detections = sv.Detections.from_ultralytics(results[0])

oriented_box_annotator = sv.OrientedBoxAnnotator()
annotated_frame = oriented_box_annotator.annotate(
    scene=cv2.imread(file_name),
    detections=detections
)

sv.plot_image(image=annotated_frame, size=(16, 16))



