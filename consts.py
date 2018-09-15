from enum import Enum

class GameResult(Enum):
	WIN = u'Win'
	LOSS = u'Loss'
	TIE = u'Tie'

class Team(Enum):
	RED = u'Red'
	BLUE = u'Blue'

class ClassType(Enum):
	SCOUT = u'scout'
	SOLDIER = u'soldier'
	PYRO = u'pyro'
	DEMOMAN = u'demoman'
	HEAVY = u'heavyweapons'
	ENGINEER = u'engineer'
	MEDIC = u'medic'
	SNIPER = u'sniper'
	SPY = u'spy'

SIXES_COMBAT_CLASSES = [ ClassType.SCOUT, ClassType.SOLDIER, ClassType.DEMOMAN ]
