from flowcat import utils, classifier, som_dataset, mappings, io_functions
from flowcat.flowcat import train_som_classifier, prepare_classifier_train_dataset


def train(data: utils.URLPath, output: utils.URLPath):
    """Train a new classifier using SOM data."""
    groups = mappings.GROUPS
    tubes = ("1", "2", "3")
    balance = {
        "CLL": 4000,
        "MBL": 2000,
        "MCL": 1000,
        "PL": 1000,
        "LPL": 1000,
        "MZL": 1000,
        "FL": 1000,
        "HCL": 1000,
        "normal": 6000,
    }
    mapping = None
    dataset = som_dataset.SOMDataset.from_path(data)
    train_dataset, validate_dataset = prepare_classifier_train_dataset(
        dataset,
        groups=groups,
        mapping=mapping,
        balance=balance)

    som_config = io_functions.load_json(data + "_config.json")

    config = classifier.SOMClassifierConfig(**{
        "tubes": {tube: som_config[tube] for tube in tubes},
        "groups": groups,
        "pad_width": 2,
        "mapping": mapping,
        "cost_matrix": None,
    })
    model = train_som_classifier(train_dataset, validate_dataset, config)

    model.save(output)
    model.save_information(output)
