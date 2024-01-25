# temp.py


# object detection by comparing current frame to previous frame, output labels
def detectRunningDiff(frame, previousframe, cls):
	# diff current and previous frames
	diff = diffFrames(frame, previousframe)
	gdebugframes.append({'diff':diff})

	# convert to gray and make mask via otsu threshold
	gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
	t, mask = cv2.threshold(gray, 0,  255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
	gdebugframes.append({'gray':gray})
	gdebugframes.append({'mask':mask})
	
	# if otsu t value is too low, it means there's no diff, no movement
	logging.info(f'diff otsu t:{t}')
	if t < gthresholdDiffT:
		logging.debug(f'low t {t}, no movement')
		return [lbl.nomovement]

	# find contours in the mask
	cnts,_ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

	# make a list of contour descriptors, dicts describing and including each contour
	cntds = []
	for cnt in cnts:
		rect = cv2.minAreaRect(cnt) 
		cntd = {'ctr':np.intp(rect[0]), 'size':rect[1], 'cnt':cnt, 'meandistance':0, 'qualified':False}
		cttds.append(cntd)

	# calculate mean distance for each contour center
	maxmean = calcMeanDistance(cntds)

	# if the means for all points are less than the vehicle size,
	# that indicates there is only the one object: the vehicle 
	# all points are qualified
	threshold = gthresholdSk8Size
	if maxmean < threshold:
		threshold = 0
		logging.debug(f'detectRunningDiff: one center only, no outliers')

	# if some points have larger means
	# there must be additional objects and outlier points
	# these outliers will increase the means for all points
	proctr, qctrs, dctrs = findProposedCenter(cntds, gthresholdSk8Size) 

#-----------
	# debugging
	printObjectArray(apts)

	# debugging, show us the bogus centerpoint you came up with
	if len(qctrs) <= 0:
		cx,cy = proctr
		qctrs.append([cx-50,cy-50])
		qctrs.append([cx+50,cy-50])
		qctrs.append([cx+50,cy+50])
		qctrs.append([cx-50,cy+50])

	qctrs = np.array(qctrs)
	qctrs = np.intp(qctrs)

	logging.debug(f'qctrs: {qctrs}')

	logging.debug(f'calcDistances num input pts:{len(ctrs)}, num output ctrs:{len(qctrs)}')
	return [qctrs, dctrs, means]
#----------------------	

	# make convex hull out of qualified points
	qpts = np.array(qctrs)
	#hull = cv2.convexHull(qpts)
	hull = detect.combineContous(cntds)

	# find rotated rect and make label of convex hull
	rect = cv2.minAreaRect(hull) 
	rmse = scr.calcRMSE(dim, rect[1])
	label = lbl.labelFromRect(cls, rect, which=False, score=rmse)
	logging.debug(f'clustered label:{label}')

	# for debugging, make an image showing the convex hull and the centerpoints
	clustered = createImage(frame.shape)
	drawContours( hull)
	drawPoints, qualified green
	drawPoints, disqualified red
	gdebugFrames.append({'clustered':clustered})

	return [label],[qpts,dpts,means] 

	
	gdebugframe = [diff, gray, mask, cluster]
	return labels

#input:current,previous  #output:diff
def diffFrames(current,previous):
	imgDiff1 = cv2.absdiff(current, previous)	
	imgDiff2 = cv2.absdiff(current, imgDiff1)
	imgDiff3 = cv2.absdiff(previous, imgDiff2)
	return imgDiff3

# an object detection algorithm, ie labelsFromMask
# choose contours that are within proximity of one another
# then make one new contour via convexHull of the centerpoints
# alternative: use all the points of the chosen contours, not just the centers
# input:mask, output:labels
def clustering(mask, cls, dim, maxcount, t):  
	ctrs = []
	sizes = []
	polygon = []
	cnts,_ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
	for cnt in cnts:
		rect = cv2.minAreaRect(cnt) 
		ctr = rect[0]
		size = rect[1]
		mean = np.mean(size)
		ctr = np.intp(ctr)
		#if size > (5,5) and size < (100,100):
		ctrs.append(ctr)
		sizes.append(size)
	
	{'ctr':ctr, 'size':size, 'cnt':cnt}

	# qualify points based on distances from other points
	[qpts,dpts,means] = calcDistances(ctrs)

	# make convex hull out of qualified points
	qpts = np.array(qpts)
	#hull = cv2.convexHull(qpts)
	hull = detect.combineContours(cnts)  # qualified contours

	# find rotated rect and make label of convex hull
	rect = cv2.minAreaRect(hull) 
	rmse = scr.calcRMSE(dim, rect[1])
	label = lbl.labelFromRect(cls, rect, which=False, score=rmse)
	logging.debug(f'clustered label:{label}')
	return [label],[qpts,dpts,means] 

		
def findProposedCenter(ctrs):
  	# input list of dicts 
	# {'ctr':ctr, 'meandistance':mean, 'cnt':cnt, 'qualified':False}

	# sort by meandistance
	ctrs = sorted(ctrs,  key=lambda a: a['meandistance'])

	# calc pct increase in meandistance from one point to the next
	homepts = []
	prevmean = ctrs[0]['meandistance']
	pct = 1
	for pt in ctrs:
		if prevmean > 0:
			pct = ((pt['meandistance'] - prevmean) / prevmean) * 100 
			pct = max(pct,1)
		prevmean = pt['meandistance']

		# save centerpoints within the meandistance threshold
		if pct < gthresholdHome:
			homepts.append(pt['ctr'])
	
	# find center of homepts
	homepts = np.array(homepts)
	proposedcenter = (np.mean(homepts[:,0]),np.mean(homepts[:,1]))
	logging.debug(f'proposedcenter: {proposedcenter}')

	return proposedcenter 

# calculate the distance between each point and every other point 
# save the mean distance for each point, return the largest
def calcMeanDistance(cntds)
	means = []
	for cntd in cntds:
		distances = []
		ptA = cntd['ctr']
		for cntd2 in cntds:	
			ptB = cntd2{'ctr2']
			lenAB = lbl.linelen(ptA,ptB)
			distances.append(lenAB)
		# save the mean of these distances
		mean = np.mean(distances)
		cntd['meandistance'] = mean  # input array is updated
		means.append(mean)
	return np.max(means) # return largest

# given input list of contour descriptors, based on mutual proximity,
# find the likely center of our object and disqualify outlier points
def qualifyByProximity(cntds, threshold):
	qctrs = []
	dctrs = []
	for cntd in cntds:
		lenpro = lbl.linelen(pt['ctr'],proctr)
		logging.debug(f'findProposedCenter distance from center: {lenpro}')
		if threshold <= 0 or lenpro < threshold:
			cntd['qualified'] = True
			qctrs.append(cntd['ctr']
		else:
			dctrs.append(cntd['ctr']
	return proctr, [qctrs], [dctrs]

# return a convex hull enclosing all of the qualified contours
def combineContours(cntds):
	polygon = []
	for cntd in cntds:
		if cntd['qualified'] == True:
			for pt in cntd['cnt']:
				polygon.append(pt[0])
	polygon = np.array(polygon)
	hull = cv2.convexHull(polygon)
	return hull

def makeConvexMask(frame, label, cntds, hull):
	# for debugging
	# normal aframe already has label 
	# this transparent image will overlay the aframe

	cmask = make blank transparent image with alpha channel
	draw hull as white polygon
	draw qualified points in green
	draw disqualified points in red

	return cmask
