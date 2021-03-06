"""
Constants and default mappings used in the current pipeline.
"""
from .types.material import Material
from .types.classifier_config import SOMClassifierConfig


PUBLIC_ENUMS = {
    "Material": Material,
}


# probe materials allowed in further processing
ALLOWED_MATERIALS = (Material.PERIPHERAL_BLOOD, Material.BONE_MARROW)

# groups without usable infiltration values
NO_INFILTRATION = ("normal")

# mapping of some legacy cohort names in order to correctly import older
# formats
NAME_MAP = {
    "HZL": "HCL",
    "HZLv": "HCLv",
    "Mantel": "MCL",
    "Marginal": "MZL",
    "CLLPL": "PL"
}

# Marker channel mapping to equalize naming
MARKER_NAME_MAP = {
    "Kappa": "kappa",
    "Lambda": "lambda",
    "FSC": "FS",
    "SSC": "SS",
}

EMPTY_MARKER_NAMES = ("nix",)

# name of main groups in defined order for plotting
ALL_GROUPS = [
    "CLL", "MBL", "MCL", "PL", "LPL", "MZL", "FL", "HCL", "HCLv", "normal"
]
GROUPS = [
    "CLL", "MBL", "MCL", "PL", "LPL", "MZL", "FL", "HCL", "normal"
]

# colors generated using: sns.cubehelix_palette(..., rot=4, dark=0.30)
ALL_GROUP_COLORS = {
    "normal": [0.9085217891881505, 0.8370827624725752, 0.768591221065728],
    "CLL": [0.9055738886413728, 0.739043864422249, 0.8390190072884551],
    "MBL": [0.7517103067488194, 0.7262718681284317, 0.8993434028795035],
    "MCL": [0.5580942913716878, 0.7641702230322297, 0.7606540856568974],
    "PL": [0.5632735863850129, 0.7221296209954403, 0.5085605049229125],
    "LPL": [0.7121389372572974, 0.5715484745851547, 0.4467703690673176],
    "MZL": [0.7106545640520181, 0.45472499408646283, 0.6139609618280656],
    "FL": [0.4744147058579195, 0.4733134421486485, 0.6950906687883702],
    "HCL": [0.27956213324673396, 0.5260342692168561, 0.5159217461417911],
    "AML": [0.3109448417252425, 0.4738501936284707, 0.24677036906731753],
    "MM": [0.45818172339819135, 0.32006635094680486, 0.20659972060918702],
    "HCLv": [0.43306366425533704, 0.21844020487376953, 0.3567325170294466],
}

# merged group mappings, most useful in classification
GROUP_MAPS = {
    "8class": {
        "groups": ["CM", "MCL", "PL", "LPL", "MZL", "FL", "HCL", "normal"],
        "map": {"CLL": "CM", "MBL": "CM"},
        "sizes": [2, 1, 1, 1, 1, 1, 1, 1, ],
    },
    "6class": {
        "groups": ["CM", "MP", "LM", "FL", "HCL", "normal"],
        "map": {
            "CLL": "CM",
            "MBL": "CM",
            "MZL": "LM",
            "LPL": "LM",
            "MCL": "MP",
            "PL": "MP",
        },
        "sizes": [2, 2, 2, 1, 1, 1, ],
    },
    "5class": {
        "groups": ["CM", "MP", "LMF", "HCL", "normal"],
        "map": {
            "CLL": "CM",
            "MBL": "CM",
            "MZL": "LMF",
            "LPL": "LMF",
            "FL": "LMF",
            "MCL": "MP",
            "PL": "MP",
            # merged classes
            "LM": "LMF",
        },
        "sizes": [2, 2, 3, 1, 1, ],
    },
    "3class": {
        "groups": ["CD5+", "CD5-", "normal"],
        "map": {
            "CLL": "CD5+",
            "MBL": "CD5+",
            "MCL": "CD5+",
            "PL": "CD5+",
            "MZL": "CD5-",
            "LPL": "CD5-",
            "FL": "CD5-",
            "HCL": "CD5-",
            # merged classes
            "CM": "CD5+",
            "MP": "CD5+",
            "LM": "CD5-",
            "LMF": "CD5-",
        },
        "sizes": [4, 4, 1, ],
    },
    "2class": {
        "groups": ["patho", "normal"],
        "map": {
            "CLL": "patho",
            "MBL": "patho",
            "MCL": "patho",
            "PL": "patho",
            "LPL": "patho",
            "MZL": "patho",
            "FL": "patho",
            "HCL": "patho",
            # merged classes
            "CM": "patho",
            "MP": "patho",
            "LM": "patho",
            "LMF": "patho",
            "CD5+": "patho",
            "CD5-": "patho",
        },
        "sizes": [1, 1],
    }
}


# Common channel configurations
CHANNEL_CONFIGS = {
    "CLL-9F": {
        1: [
            "FS INT LIN",
            "SS INT LIN",
            "FMC7-FITC",
            "CD10-PE",
            "IgM-ECD",
            "CD79b-PC5.5",
            "CD20-PC7",
            "CD23-APC",
            "CD19-APCA750",
            "CD5-PacBlue",
            "CD45-KrOr",
        ],
        2: [
            "FS INT LIN",
            "SS INT LIN",
            "Kappa-FITC",
            "Lambda-PE",
            "CD38-ECD",
            "CD25-PC5.5",
            "CD11c-PC7",
            "CD103-APC",
            "CD19-APCA750",
            "CD22-PacBlue",
            "CD45-KrOr",
        ],
        3: [
            "FS INT LIN",
            "SS INT LIN",
            "CD8-FITC",
            "CD4-PE",
            "CD3-ECD",
            "CD56-APC",
            "CD19-APCA750",
            "HLA-DR-PacBlue",
            "CD45-KrOr"
        ],
    }
}


# canonical plotting views used by MLL
PLOT_2D_VIEWS = {
    "1": (
        ("CD19-APCA750", "CD79b-PC5.5"),
        ("CD19-APCA750", "CD5-PacBlue"),
        ("CD20-PC7", "CD23-APC"),
        ("CD19-APCA750", "CD10-PE"),
        ("CD19-APCA750", "FMC7-FITC"),
        ("CD20-PC7", "CD5-PacBlue"),
        ("CD19-APCA750", "IgM-ECD"),
        ("CD10-PE", "FMC7-FITC"),
        ("SS INT LIN", "FS INT LIN"),
        ("CD45-KrOr", "SS INT LIN"),
        ("CD19-APCA750", "SS INT LIN"),
    ),
    "2": (
        ("CD19-APCA750", "Lambda-PE"),
        ("CD19-APCA750", "Kappa-FITC"),
        ("Lambda-PE", "Kappa-FITC"),
        ("CD19-APCA750", "CD22-PacBlue"),
        ("CD19-APCA750", "CD103-APC"),
        ("CD19-APCA750", "CD11c-PC7"),
        ("CD25-PC5.5", "CD11c-PC7"),
        ("Lambda-PE", "Kappa-FITC"),
        ("SS INT LIN", "FS INT LIN"),
        ("CD45-KrOr", "SS INT LIN"),
        ("CD19-APCA750", "SS INT LIN"),
    ),
    "3": (
        ("CD3-ECD", "CD4-PE"),
        ("CD3-ECD", "CD8-FITC"),
        ("CD4-PE", "CD8-FITC"),
        ("CD56-APC", "CD3-ECD"),
        ("CD4-PE", "HLA-DR-PacBlue"),
        ("CD8-FITC", "HLA-DR-PacBlue"),
        ("CD19-APCA750", "CD3-ECD"),
        ("SS INT LIN", "FS INT LIN"),
        ("CD45-KrOr", "SS INT LIN"),
        ("CD3-ECD", "SS INT LIN")
    )
}

DEFAULT_REFERENCE_SOM_ARGS = {
    "marker_name_only": False,
    "max_epochs": 10,
    "batch_size": 50000,
    "initial_radius": 16,
    "end_radius": 2,
    "radius_cooling": "linear",
    # "marker_images": sommodels.fcssom.MARKER_IMAGES_NAME_ONLY,
    "map_type": "toroid",
    "dims": [32, 32, -1],
    "scaler": "MinMaxScaler",
}

DEFAULT_TRANSFORM_SOM_ARGS = {
    "max_epochs": 4,
    "batch_size": 50000,
    "initial_radius": 4,
    "end_radius": 1,
}

DEFAULT_CLASSIFIER_CONFIG = SOMClassifierConfig(
    tubes=None,
    groups=GROUPS,
    pad_width=2,
    mapping=None,
    cost_matrix=None,
    train_epochs=20,
    train_batch_size=32,
    valid_batch_size=128,
)

DEFAULT_CLASSIFIER_ARGS = {
    "split_ratio": 0.9,
    "split_stratify": True,
    "balance": {
        "CLL": 4000,
        "MBL": 2000,
        "MCL": 1000,
        "PL": 1000,
        "LPL": 1000,
        "MZL": 1000,
        "FL": 1000,
        "HCL": 1000,
        "normal": 6000,
    },
    "config": DEFAULT_CLASSIFIER_CONFIG,
}

DEFAULT_TRAIN_ARGS = {
    "reference": DEFAULT_REFERENCE_SOM_ARGS,
    "transform": DEFAULT_TRANSFORM_SOM_ARGS,
    "classifier": DEFAULT_CLASSIFIER_ARGS,
}
