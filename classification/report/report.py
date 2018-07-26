"""Create simple overviews over created experiments."""
import os

from functools import reduce

from scipy.stats import ttest_ind
import numpy as np

from .overview import Overview
from .misclassifications import Misclassifications
from .confusion import Confusion

from .prediction import top1_uncertainty, top2

from .file_utils import load_predictions


def generate_report(path):
    os.makedirs(path, exist_ok=True)
    # Overview().write(path)
    # Prediction().write(path)
    # Misclassifications().write(path)
    # mis = Misclassifications()
    # print(mis.get_misclassifications(["cll_normal"]))

    # conf = Confusion()

    # sel_set = conf.classification_files[
    #     conf.classification_files["set"] == "abstract_single_groups"
    # ]

    # rand_set = conf.classification_files[
    #     (conf.classification_files["set"] == "cd5_threeclass")
    #     # & (conf.classification_files["name"] == "normal_dedup")
    #     & (conf.classification_files["name"] == "somcombined_dedup")
    # ]
    # print(rand_set)

    # sel_set = conf.classification_files[
    #     (conf.classification_files["set"] == "cd5_threeclass")
    #     # & (conf.classification_files["name"] == "normal_dedup")
    #     & (conf.classification_files["name"] == "somcombined_dedup")
    # ]
    # print(sel_set)

    # rand_set = conf.get_confusion_matrices(rand_set)
    # sel_set = conf.get_confusion_matrices(sel_set)
    # rand_accs = [
    #     e for l in rand_set.apply(conf.calc_confusion_matrix, axis=1)
    #     for e in l
    # ]
    # sel_accs = [
    #     e for l in sel_set.apply(conf.calc_confusion_matrix, axis=1)
    #     for e in l
    # ]
    # print("Random: {}".format(np.mean(rand_accs)))
    # print("Selected: {}".format(np.mean(sel_accs)))
    # result = ttest_ind(rand_accs, sel_accs)
    # print(result)

    # rand_set = conf.classification_files[]

    # for sname, eset in conf.get_experiment_sets(sel_set):
    #     eset = conf.get_confusion_matrices(sname, eset)
    #     eset.apply(conf.calc_confusion_matrix, axis=1)
    # conf.get_confusion_matrices()

    mis = Misclassifications()

    infil_set = mis.data[
        (mis.data["set"] == "cd5_threeclass")
        # & (conf.classification_files["name"] == "normal_dedup")
        & (mis.data["name"] == "somcombined_dedup")
    ]
    misclass = mis.get_misclassifications(infil_set)

    labels = misclass.index.get_level_values("id")

    infiltrations = mis.get_infiltrations(infil_set).reset_index()
    misclass_infil = infiltrations[infiltrations["label"].isin(labels)]
    print(misclass_infil.mean())

    hi_infil_misclass = misclass_infil[misclass_infil["infiltration"] > 20.0]
    print(hi_infil_misclass)

    non_misclass_infil = infiltrations[~infiltrations["label"].isin(labels)]
    print(non_misclass_infil.mean())

    for _, row in infil_set.iterrows():
        preds = load_predictions(row["predictions"])
        hi_infil = [p[(p["infiltration"] > 5.0) | (p["group"] == "normal")] for p in preds.values()]
        preds = [top1_uncertainty(h, threshold=0.0) for h in hi_infil]
        for p in preds:
            print(p)


    single_exp = mis.data.loc["abstract_single_groups", "somgated", "random"]
    single_pred = load_predictions(single_exp["predictions"])
    t2_preds = [top2(p) for p in single_pred.values()]
    avgs = []
    for i, p in enumerate(t2_preds):
        pred = list(single_pred.values())[i]
        gcount = pred.groupby("group").size()
        weighted_avg = sum(gcount * p["correct"]) / sum(gcount)
        print("Weighted avg: ", weighted_avg)
        avgs.append(weighted_avg)
    print("Avg acc: ", np.mean(avgs))

    conf = Confusion()

    sel_exp = conf.classification_files.loc[
        (conf.classification_files["name"] == "somgated")
        & (conf.classification_files["set"] == "abstract_single_groups")
    ]
    confusions = conf.get_confusion_matrices(sel_exp)["confusion"].iloc[0]

    sum_confusion = reduce(lambda x, y: x + y, confusions)
