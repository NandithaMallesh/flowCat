# General notes
NOTE = Process using both tube1 and tube2 without misjoined normal

# processing options
# GROUPS = LPL;MZL;MCL;PL;CLL;MBL;FL;normal
# GROUPS = LMg:LPL,MZL;MtCp:MCL,PL;CM:CLL,MBL;FL;normal
GROUPS = LMg:LPL,MZL;MtCp:MCL,PL;CM:CLL,MBL
# GROUPS = CLL;normal
METHOD = kfold:5
# FILTERS = smallest
FILTERS =
TUBES = 1;2
