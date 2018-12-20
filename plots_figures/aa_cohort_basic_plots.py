# pylint: skip-file
# flake8: noqa
"""Overview plots to be generated for a given case_info file."""
import json
import argparse
import pathlib
import datetime
import collections

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

# set some sane seaborn defaults
sns.set()


# patch datetime if fromisoformat does not exist
if not hasattr(datetime.date, "fromisoformat"):
    def fromisoformat(datestring):
        return datetime.datetime.strptime(datestring, "%Y-%m-%d").date()
else:
    fromisoformat = datetime.date.fromisoformat


def get_args():
    parser = argparse.ArgumentParser(description="Basic overview plots of a cohort dataset. Enter two to compare them.")
    parser.add_argument("--date", help="Cutoff date for testing.", type=fromisoformat)
    parser.add_argument("caseinfo", help="Json file containing case information", type=pathlib.Path, nargs="+")
    return parser.parse_args()


def load_caseinfo(cpaths):
    """Load caseinfo json file."""
    cinfos = []
    for cpath in cpaths:
        with open(str(cpath)) as infofile:
            cinfo = json.load(infofile)
        cinfos.append(cinfo)
    return cinfos


def get_dataset_date(path):
    dataset = path.parent.name
    date = fromisoformat(path.stem.split("_")[-1])
    return dataset, date


def print_stats(cpath, cinfo, pfun=print):
    """Get summary statistics on the caseinfo file."""
    dataset, date = get_dataset_date(cpath)
    pfun(f"# {dataset}\n")
    pfun(f"Case info generated on {date}.")

    # number of samples
    pfun(f"Number of samples: {len(cinfo)}")

    # number of groups
    groups = set(c["cohort"] for c in cinfo)
    pfun(f"{len(groups)} groups: {' '.join(groups)}")

    # by date
    dates = collections.defaultdict(lambda: collections.defaultdict(list))
    for c in cinfo:
        d = fromisoformat(c["date"])
        dates[d.year][d.month].append(c)

    for y in sorted(dates.keys()):
        months = dates[y]
        for m in sorted(months.keys()):
            pfun(f"{y}-{m}: {len(months[m])}")

    # duplicates
    labels = collections.defaultdict(list)
    for c in cinfo:
        labels[c["id"]].append(c["cohort"])
    for l in filter(lambda x: len(labels[x]) > 1, labels):
        pfun(f"{l}: {labels[l]}")


def print_diff(cpaths, cinfos, pfun=print):
    p1, p2 = cpaths
    c1, c2 = cinfos
    pfun(f"# {get_dataset_date(p1)[0]} v {get_dataset_date(p2)[0]}\n")
    pfun(f"Num cases: {len(c1)} v {len(c2)}: Δ{len(c2) - len(c1)}")

    c1groups = {c["cohort"] for c in c1}
    c2groups = {c["cohort"] for c in c2}
    groups = c1groups | c2groups
    pfun(f"Num groups: {len(c1groups)} v {len(c2groups)}")
    for group in sorted(groups):
        l1 = sum(1 for c in c1 if c["cohort"] == group)
        l2 = sum(1 for c in c2 if c["cohort"] == group)
        pfun(f"{group}: {l1} v {l2}: Δ{l2 - l1}")
        if group == "MCL":
            missing = {c["id"] for c in c1 if c["cohort"] == group} - {c["id"] for c in c2 if c["cohort"] == group}
            print("\n".join(missing))


def print_window(cinfo, start=None, end=None, less=None, more=None):

    if less is None:
        less = lambda x, y: x <= y
    if more is None:
        more = lambda x, y: x >= y

    def inwindow(dstr):
        d = fromisoformat(dstr)
        if start and end:
            return less(d, end) and more(d, start)
        elif start:
            return more(d, start)
        elif end:
            return less(d, end)
        else:
            return True

    window = collections.Counter(
        c["cohort"] for c in cinfo if inwindow(c["date"])
    )
    print(f"Window from {start} to {end}")
    print("\n".join(f"{k}: {v}" for k, v in window.items()))
    return window


def plot_cohorts(data, title):
    """Create a simple barchart for cohort numbers."""
    fig, ax = plt.subplots()
    sns.barplot(x=list(data.keys()), y=list(data.values()), ax=ax)
    for i, (name, count) in enumerate(data.items()):
        ax.text(i, count, count, color="black", ha="center")
    # ax.set_title(title)
    print(title)
    plt.savefig("test.png", dpi=300)
    plt.close("all")


def print_ratio(num, den):
    print(f"All: {sum(num.values())} / {sum(den.values())}")
    print("\n".join(f"{k}: {num[k]} / {den[k]} ({num[k] / den[k]:.2f})" for k in den))


def train_test_specification(cinfo):
    test_start = fromisoformat("2018-04-01")
    test_end = fromisoformat("2018-10-01")

    all_num = collections.Counter(c["cohort"] for c in cinfo)

    train_num = print_window(cinfo, end=test_start, less=lambda x, y: x < y)
    test_num = print_window(cinfo, test_start, test_end)

    print_ratio(test_num, train_num + test_num)
    oldest = min(fromisoformat(c["date"]) for c in cinfo)
    newest = max(fromisoformat(c["date"]) for c in cinfo)
    plot_cohorts(all_num, f"All cohorts from {oldest} to {newest}")


def main():
    args = get_args()
    cinfos = load_caseinfo(args.caseinfo)

    for cpath, cinfo in zip(args.caseinfo, cinfos):
        print_stats(cpath, cinfo)
        print("\n")

    if len(cinfos) == 2:
        print_diff(args.caseinfo, cinfos)
    elif len(cinfos) > 2:
        print("Diff with more than 2 caseinfos currently not supported.")

if __name__ == "__main__":
    main()