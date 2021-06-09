'''

x yellow half on the ground needs work

x left/right is reversed 

x when we switch from spot to pad, yaw goes to +90
	spot w is 0
	pad angle is 359 degrees
	how to calculate desired change in angle
		only necessary when landing
		otherwise, arbitrary
		perhaps used in orienting
	for now
		desired angle is zero
		if angle is greater than 180, positive 360 - angle
		if angle is less than 180, negative angle

x hover lower

x nonadjacent state is non-helpful




basemap 

orient framemap to basemap

add new elements from framemap to basemap

use the mbox data and scale is constant          


why does each map have an agl associated?
	that is valid only for its original frame and objects

basemap uses dbox only for drawing


framemap

framemap, hover on pad, ascend to two meters, initiate basemap

initiate basemap
	copy framemap to basemap
	make pad center the null_island
	shift objects accordingly
		pad x,y
		spot
		cones
		arena
		drone position

orient framemap to basemap, using only cones
	if framemap has more cones, higher agl
	if framemap has fewer cones, lower agl
	if framemap has same number of cones
	irregardless
		choose three cones nearest the drone position, ie center of the framemap
		find three cones with same angles in the basemap	
		measure angles and distances between all cones
		from each cone, to all other cones
		is constant until basemap changed

cone1
	distance to cone2
	distance to cone3
	angle between cone2 and cone3
	distance to cone4
	angle between cone2 and cone4
	angle between cone3 and cone4
	distance to cone5
	angle between cone2 and cone5
	angle between cone3 and cone5
	angle between cone4 and cone5

cone 1
	find cone2 with same distance as framemap
	use cone1 and cone2
	compare distance and angle to remaining cones

multiple candidates for cone2


the drone may have been yawing, so we don't know its angle
angles among cones will match
not absolute geographic angles

there is no angle between two cones
an angle exists between three cones
between one cone and two others




otherwise,
	orient framemap to basemap
	add new elements from framemap to basemap	

basemap may need to grow in all directions
so it must have a constant centerpoint
is that true?

after liftoff, pad position is center of basemap
cones discovered are mapped 
'''

	def orient(self, basemap, framemap):
		# choose three adjacent cones, a,b,c nearest center of framemap
		angle abc
		len ba
		len bc

		# find matching three cones in basemap
			# maybe start from last known drone position

		# make array of candidates
		a = [
			[angle, len1, len2],	# abc
			[angle, len1, len2],	# abd
		]

		# twist the framemap to match the basemap
			# plot point u straight
			# compare abu between basemap and framemap

		# center, twist, and stretch the framemap to match the basemap center and scale

		# compare all cones by centerpoint
			# extra cones in framemap, new, add to basemap
			# missing cones in framemap, offscreen, ignore
			# other mismatched cones, fucked up, start over

		# plot drone position on basemap

		# plot pad position on basemap


	def snapBasemap(self, framemap):
		# one-time creation of basemap; do before moving wheels



