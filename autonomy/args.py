'''
arena_spec = {
	'w':4000,
	'h': 4000,
	'title': 'Arena',
	'gate': [2000,50],
	'conecolor': 'cyan',
	'routecolor': 'black'
}
event_spec = {
	'event': 'freestyle',
	'num_cones': 5,
}
skate_spec = {
	'turning_radius': 200,
	'length': 140, # 70,
	'width':  20,
	'avgspeed': 45, # kmh, realistic:15  # bugs appear above 30
	'color': 'red',
	'helmlag': 0,
	'helmpct': .30,
	'helmrange': [-45,+45],
	'drift': 0,
}

run_spec = {
	'quiet': False,
	'fps':20,         # frames per second
	'simmode': None,  # precise, helmed
	'startdelay': 1000,
	'trail': 'none'   # none, full, lap
}
'''
import argparse
import types

event_names = [
	'freestyle',
	'barrel-racing',
	'course-racing',
	'straight-line-slalom',
	'downhill-slalom',
	'spiral',
]

if __name__ == '__main__':
	parser = argparse.ArgumentParser()

	# arena spec
	parser.add_argument('-aw' , '--arenawidth'	,default=4000		,type=int				,help='width of arena in pixels'	),
	parser.add_argument('-ah' , '--arenaheight'	,default=4000		,type=int				,help='height of arena in pixels'	),
	parser.add_argument('-gx' , '--gatex'		,default=2000		,type=int				,help='x position of starting gate'	),
	parser.add_argument('-gy' , '--gatey'		,default=50		,type=int				,help='y position of starting gate'	),

	# sim spec
	parser.add_argument('-q'  , '--quiet'		,default=False		,action='store_true'			,help='run without console messages'	),
	parser.add_argument('-v'  , '--verbose'		,default=False		,action='store_true'			,help='show detailed console messages'	),
	parser.add_argument('-sm' , '--simmode'		,default='precise'	,choices=['precise', 'helmed']		,help='simulation mode'			),
	parser.add_argument('-d'  , '--drift'		,default=0		,type=int				,help='maximum drift in degrees'	), 
	parser.add_argument('-td' , '--suite'		,default='none'		,choices=['','']			,help='name of test data suite'		),

	# run spec
	parser.add_argument('-t'  , '--trail'		,default='none'		,choices=['none', 'full', 'lap']	,help='trail left by skate'		), 
	parser.add_argument('-o'  , '--output'		,default='none'							,help='output filename'			),
	parser.add_argument('-f'  , '--fps'		,default=20		,type=int				,help='frames per second'		),
	parser.add_argument('-sd' , '--startdelay'	,default=1000		,type=int				,help='delay milliseconds before start' ),
	parser.add_argument('-cc' , '--conecolor'	,default='cyan'							,help='color of cones'			),
	parser.add_argument('-rc' , '--routecolor'	,default='black'						,help='color of route'			),

	# event spec
	parser.add_argument('-e'  , '--event'		,default='freestyle'	,choices=event_names			,help='name of event'			),
	parser.add_argument('-nc' , '--numcones'	,default=5		,type=int				,help='number of cones'			),

	# skate spec
	parser.add_argument('-tr' , '--turningradius'	,default=200		,type=int				,help='skate turning radius'		),
	parser.add_argument('-sl' , '--skatelength'	,default=70		,type=int				,help='skate length in cm'		),
	parser.add_argument('-sw' , '--skatewidth'	,default=20		,type=int				,help='skate width in cm'		),
	parser.add_argument('-sc' , '--skatecolor'	,default='red'							,help='skate color'			),
	parser.add_argument('-as' , '--avgspeed'	,default=15		,type=int				,help='average speed'			),
	parser.add_argument('-hl' , '--helmlag'		,default=0		,type=int				,help='lag before helm takes effect'	),
	parser.add_argument('-hp' , '--helmpct'		,default=30		,type=int				,help='percent of relative bearing'	),
	parser.add_argument('-hr' , '--helmrange'	,default=45		,type=int				,help='range of helm in degrees =/-'	),


	spec = parser.parse_args()	# returns Namespace object, use dot-notation
	speca = vars(spec)		# returns iterable and subscriptable collection

	print(spec)
	print(speca)

	print(spec.simmode)
	print(speca['simmode'])

	spec.simmode = 'helmed'
	print(parser.get_default('simmode'))

	for k in speca:
		tab = '\t' if len(k) >= 8 else '\t\t'
		print(f'{k}{tab}{speca[k]}')

	# iterate argparse.Namespace __dict__ attribute
	print('----')
	for k in spec.__dict__:
		tab = '\t' if len(k) >= 8 else '\t\t'
		print(f'{k}{tab}{spec.__dict__[k]}')
	print('----')

	# initialize a argparse.Namespace from a dict
	sp = argparse.Namespace(**speca)
	sp.a = 'a'
	print(sp)
	print('----')

	# roughly equivalent: argparse.Namespace vs types.SimpleNamespace
	sn = types.SimpleNamespace(**speca)
	sn.a = 'b'
	print(sn)

