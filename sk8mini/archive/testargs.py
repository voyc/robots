'''
testargs.py

argparse boolean keywords
action='store_true'  implies type=boolean,  default=False
action='store_false' implies type=boolean,  default=True

use of store_false is misleading
always use store_true

--crop   action=store_true   # force an action
--nocrop action=store_true   # suppress an action
'''
import argparse

def hoo():
	global hoo
	hoo = 'hoo'
	print(hoo)
	
global args
parser = argparse.ArgumentParser()
parser.add_argument('-cr' ,'--crop'     ,action='store_true'  ,help='crop'                 ) 
parser.add_argument('-ca' ,'--nocal'	,action='store_false' ,help='suppress calibrate'              )
args = parser.parse_args()	# returns Namespace object, use dot-notation

print(f'crop {args.crop}')
print(f'nocal {args.nocal}')
hoo()
print(hoo)

parser2 = argparse.ArgumentParser()
parser2.add_argument('-pr' ,'--process'  ,default='awacs'      ,help='process'              ) 
parser2.add_argument('-ca' ,'--nocal'	,action='store_false' ,help='suppress calibrate'              )
parser2.add_argument('--shortcut'	,default='noshorty'   ,help='no shorty'         )
args2 = parser2.parse_args()	# returns Namespace object, use dot-notation

print(f'process {args2.process}')
print(f'nocal {args2.nocal}')
print(f'nocal {args2.shortcut}')
'''

	parser.add_argument('-v'  ,'--verbose'  default false                      ,action='store_true'        ,help='verbose comments'                 ) 
	parser.add_argument('-q'  ,'--quiet'    default false                      ,action='store_true'        ,help='suppress all output'              )

	parser.add_argument('-ps' ,'--process'                        ,default=rdef.process       ,help='process: both,skate,awacs,none'   )

	parser.add_argument('-sm' ,'--sim'                            ,action='store_true'        ,help='simulation mode'                  )
	parser.add_argument('-cr' ,'--crop'   delete
	parser.add_argument('-ns' ,'--nosave'   add no                        ,action='store_true'        ,help='save image to disk'               )
	parser.add_argument('-nv' ,'--noshow'   add no                       ,action='store_true'        ,help='show visualization'               )

	parser.add_argument('-nc' ,'--nocal'    add                        ,action='store_true'        ,help='show visualization'               )

'''

