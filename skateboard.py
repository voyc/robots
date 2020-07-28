#!/usr/bin/python
import jetson.inference
import jetson.utils
import argparse

# parse the command line
parser = argparse.ArgumentParser()
parser.add_argument("filename", type=str, help="filename of the image to process")
parser.add_argument("--network", type=str, default="googlenet", help="model to use, can be googlenet, resnet-18, etc. (see --help for others)")
opt = parser.parse_args()

# load the image
img, width, height = jetson.utils.loadImageRGBA(opt.filename)

# load the recognition network
net = jetson.inference.imageNet(opt.network)

# classify the image
class_idx, confidence = net.Classify(img, width, height)

# find the object description
class_desc = net.GetClassDesc(class_idx)

# print out the result
print("image is recognized as '{:s}' (class #{:d}) with {:f}% confidence".format(class_desc, class_idx, confidence * 100))

