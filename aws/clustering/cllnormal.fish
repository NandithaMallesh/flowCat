#!/usr/bin/fish

source ../lib/run_batch.fish

# Create experiments for indiv pregating
set TAG "cllnormal"

set RAND 10

set EXPERIMENTS "cllnormal"

for i in (seq 1 $RAND)
	set expname $TAG"_run_"$i
	batchsub $expname "run" $TAG.mk $TAG $i
end