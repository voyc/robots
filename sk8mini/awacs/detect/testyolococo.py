'''
testyolo.py - test yolo object detection
https://pyimagesearch.com/2018/11/12/yolo-object-detection-with-opencv/

$ python3 testyolococo.py --image photos/training/00095.jpg --yolo ~/media/webapps/nn/yolococo


three primary object detectors you’ll encounter:
	R-CNN and their variants, including the original R-CNN, Fast R- CNN, and Faster R-CNN
	Single Shot Detector (SSDs)
	YOLO

R-CNNs are one of the first deep learning-based object detectors and are an 
example of a two-stage detector.

R-CNN 
Rich feature hierarchies for accurate object detection and semantic segmentation, (2013) Girshick et al.
https://arxiv.org/abs/1311.2524
proposed an object detector that required an algorithm such as 
Selective Search (or equivalent) to propose candidate bounding boxes that could contain objects.

These regions were then passed into a CNN for classification, 
ultimately leading to one of the first deep learning-based object detectors.

The problem with the standard R-CNN method was that it was painfully slow and 
not a complete end-to-end object detector.

Fast R-CNN, (2013) Girshick et al.
https://arxiv.org/abs/1504.08083

The Fast R-CNN algorithm made considerable improvements to the original R-CNN, 
namely increasing accuracy and reducing the time it took to perform a forward pass; 
however, the model still relied on an external region proposal algorithm.

Faster R-CNN: Towards Real-Time Object Detection with Region Proposal Networks, (2015) Girshick et al.
https://arxiv.org/abs/1506.01497

R-CNNs became a true end-to-end deep learning object detector by 
removing the Selective Search requirement and instead relying on a
Region Proposal Network (RPN) that is 
(1) fully convolutional and 
(2) can predict the object bounding boxes and “objectness” scores 
(i.e., a score quantifying how likely it is a region of an image may contain an image). 
The outputs of the RPNs are then passed into the R-CNN component for final classification and labeling.

While R-CNNs tend to be very accurate, 
the biggest problem with the R-CNN family of networks is their speed — they were incredibly slow, 
obtaining only 5 FPS on a GPU.

To help increase the speed of deep learning-based object detectors, 
both Single Shot Detectors (SSDs) and YOLO use a one-stage detector strategy.

These algorithms treat object detection as a regression problem, 
taking a given input image and simultaneously learning bounding box coordinates and 
corresponding class label probabilities.

In general, single-stage detectors tend to be less accurate than two-stage detectors but are 
significantly faster.

YOLO is a great example of a single stage detector.

"You Only Look Once: Unified, Real-Time Object Detection" 2015, Redmon et al.
details an object detector capable of super real-time object detection, 
obtaining 45 FPS on a GPU.

Note: A smaller variant of their model called “Fast YOLO” claims to achieve 155 FPS on a GPU.

YOLO has gone through a number of different iterations, including 
YOLO9000: Better, Faster, Stronger (i.e., YOLOv2), capable of detecting over 9,000 object detectors.

Redmon and Farhadi are able to achieve such a large number of object detections by 
performing joint training for both object detection and classification. 
Using joint training the authors trained YOLO9000 simultaneously on both 
the ImageNet classification dataset and COCO detection dataset. 
The result is a YOLO model, called YOLO9000, that can predict detections for object classes 
that don’t have labeled detection data.

While interesting and novel, YOLOv2’s performance was a bit underwhelming 
given the title and abstract of the paper.

On the 156 class version of COCO, YOLO9000 achieved 16% mean Average Precision (mAP), and yes, 
while YOLO can detect 9,000 separate classes, the accuracy is not quite what we would desire.

"YOLOv3: An Incremental Improvement" (2018) Redmon and Farhadi
YOLOv3 is significantly larger than previous models but is, in my opinion, 
the best one yet out of the YOLO family of object detectors.

We’ll be using YOLOv3 in this blog post, in particular, YOLO trained on the COCO dataset.

-------------
https://arxiv.org/pdf/1804.02767.pdf

"...backbone, darknet 53, 53 convolutional layers..."
This new network is much more powerful than Darknet19 but still more efficient than ResNet-101 or ResNet-152.
Here are some ImageNet results:

backbone
	darknet 19
	resnet 101
	resnet 152
	darknet 53
	Retina Net


---------------------
COCO

The COCO dataset consists of 80 labels, including, but not limited to:
	People
	Bicycles
	Cars and trucks
	Airplanes
	Stop signs and fire hydrants
	Animals, including cats, dogs, birds, horses, cows, and sheep, to name a few
	Kitchen and dining objects, such as wine glasses, cups, forks, knives, spoons, etc.
	… and much more!
https://github.com/pjreddie/darknet/blob/master/data/coco.names



'''
import numpy as np
import argparse
import time
import cv2
import os

# construct the argument parse and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-i", "--image", required=True, help="path to input image")
ap.add_argument("-y", "--yolo", required=True, help="base path to YOLO directory")
ap.add_argument("-c", "--confidence", type=float, default=0.5, help="minimum probability to filter weak detections")
ap.add_argument("-t", "--threshold", type=float, default=0.3, help="threshold when applying non-maxima suppression")
args = vars(ap.parse_args())

# load the COCO class labels our YOLO model was trained on
labelsPath = os.path.sep.join([args["yolo"], "coco.names"])
LABELS = open(labelsPath).read().strip().split("\n")

# initialize a list of colors to represent each possible class label
np.random.seed(42)
COLORS = np.random.randint(0, 255, size=(len(LABELS), 3), dtype="uint8")

# derive the paths to the YOLO weights and model configuration
weightsPath = os.path.sep.join([args["yolo"], "yolov3-tiny.weights"])
configPath = os.path.sep.join([args["yolo"], "yolov3-tiny.cfg"])

# load our YOLO object detector trained on COCO dataset (80 classes)
print("[INFO] loading YOLO from disk...")
net = cv2.dnn.readNetFromDarknet(configPath, weightsPath)

# load our input image and grab its spatial dimensions
image = cv2.imread(args["image"])
(H, W) = image.shape[:2]

# determine only the *output* layer names that we need from YOLO
#ln = net.getLayerNames()
#ln = [ln[i[0] - 1] for i in net.getUnconnectedOutLayers()]
lnall = net.getLayerNames()
uncon = net.getUnconnectedOutLayers()
ln = []
for i in uncon:
	ln.append(lnall[i-1])

# construct a blob from the input image 
blob = cv2.dnn.blobFromImage(image, 1 / 255.0, (416, 416), swapRB=True, crop=False)
net.setInput(blob)

# perform a forward pass of the YOLO object detector, 
# giving us our bounding boxes and associated probabilities
start = time.time()
layerOutputs = net.forward(ln)
end = time.time()
print("[INFO] YOLO took {:.6f} seconds".format(end - start))

# initialize our lists of detected bounding boxes, confidences, and class IDs, respectively
boxes = []
confidences = []
classIDs = []

# loop over each of the layer outputs
for output in layerOutputs:
	# loop over each of the detections
	for detection in output:
		# extract the class ID and confidence
		scores = detection[5:]
		classID = np.argmax(scores)
		confidence = scores[classID]

		# filter out weak predictions by ensuring the detected
		# probability is greater than the minimum probability
		if confidence > args["confidence"]:

			# scale the bounding box coordinates back relative to the # size of the image
			# YOLO returns the center (x, y) and size
			box = detection[0:4] * np.array([W, H, W, H]) 
			(centerX, centerY, width, height) = box.astype("int")

			# use the center (x, y) to top-left
			x = int(centerX - (width / 2))
			y = int(centerY - (height / 2))

			# update our lists of bounding box coordinates, confidences, and class IDs
			boxes.append([x, y, int(width), int(height)])
			confidences.append(float(confidence))
			classIDs.append(classID)

# apply non-maxima suppression to suppress weak, overlapping bounding boxes
idxs = cv2.dnn.NMSBoxes(boxes, confidences, args["confidence"], args["threshold"])

# ensure at least one detection exists
if len(idxs) > 0:
	# loop over the indexes we are keeping
	for i in idxs.flatten():
		# extract the bounding box coordinates
		(x, y) = (boxes[i][0], boxes[i][1])
		(w, h) = (boxes[i][2], boxes[i][3])
		# draw a bounding box rectangle and label on the image
		color = [int(c) for c in COLORS[classIDs[i]]]
		cv2.rectangle(image, (x, y), (x + w, y + h), color, 2)
		text = "{}: {:.4f}".format(LABELS[classIDs[i]], confidences[i])
		cv2.putText(image, text, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

# show the output image
cv2.imshow("Image", image)
while 1:
	key = cv2.waitKey(0)
	if key == ord('q'):
		break

