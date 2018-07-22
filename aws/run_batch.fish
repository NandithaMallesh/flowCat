#!/usr/bin/fish
# Define some convenience features for AWS Batch control

set QUEUE "GPU-Queue"
set DEFINITION "Clustering:11"

set opt --output text

set STATUS SUBMITTED PENDING RUNNABLE STARTING RUNNING

function batchjobs
	for stat in $STATUS
		aws batch list-jobs --job-queue $QUEUE --job-status $stat $opt | awk '{print $4}'
	end
end

function batchls
	aws batch describe-job-definitions --status ACTIVE $opt | awk 'BEGIN { FS = "[ \t]+" };/JOBDEFINITIONS/ {print $3 ":" $4}'
end

function batchsub
	set jobname $argv[1]
	if not contains $jobname (batchjobs)
		if [ (count $argv) -ge 3 ]
			aws batch submit-job --job-definition $DEFINITION --job-queue $QUEUE --job-name $jobname --parameters target=$argv[2] --container-overrides environment="[{name=EXP_NAME,value=$argv[3]},{name=TAG_NAME,value=$argv[4]}]"
		else if [ (count $argv) -eq 2 ]
			aws batch submit-job --job-definition $DEFINITION --job-queue $QUEUE --job-name $jobname --container-overrides command=$argv[2]
		else
			aws batch submit-job --job-definition $DEFINITION --job-queue $QUEUE --job-name $jobname
		end
	else
		echo "$jobname already submitted"
	end
end

# set RUNTYPES "run" "run-selected"

set RUNTYPES "run"

function submit_jobs
	set TAG $argv[1]
	set RAND $argv[2]
	set EXPERIMENTS $argv[3..-1]
	for experiment in $EXPERIMENTS
		set expfile $TAG/$experiment.mk
		for run in $RUNTYPES
			for i in (seq 1 $RAND)
				set expname $TAG"_"$experiment"_"$run"_"$i
				echo "Creating $run $expname with $expfile"
				batchsub $expname $run $expfile $TAG
			end
		end
	end
end
