TAG := $(shell basename $(dir $(lastword $(MAKEFILE_LIST))))_
METHOD = kfold:10
TUBES = 1;2

GROUPS = --group "CLL;normal"
SIZE = 
FILTERS = 
