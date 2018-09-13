import pickle
import pathlib

import numpy as np
import pandas as pd
from sklearn import manifold, model_selection, preprocessing
from sklearn import naive_bayes
from sklearn import metrics

import keras
from keras import layers, models, regularizers, optimizers
from keras.utils import plot_model
from keras_applications import resnet50

from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure

import weighted_crossentropy

import sys
sys.path.append("../classification")
from classification import plotting


COLS = "grcmyk"


def plot_transformed(path, tf1, tf2, y):
    """Plot transformed data with colors for labels."""

    path.mkdir(parents=True, exist_ok=True)
    figpath = path / "decompo"

    fig = Figure(figsize=(10, 5))

    axes = fig.add_subplot(121)
    for i, group in enumerate(y.unique()):
        sel_data = tf1[y == group]
        axes.scatter(sel_data[:, 0], sel_data[:, 1], label=group, c=COLS[i])
    axes.legend()

    axes = fig.add_subplot(122)
    for i, group in enumerate(y.unique()):
        sel_data = tf2[y == group]
        axes.scatter(sel_data[:, 0], sel_data[:, 1], label=group, c=COLS[i])
    axes.legend()

    FigureCanvas(fig)
    fig.savefig(figpath)


def load_dataset(path):
    """Return dataframe containing columns with filename and labels."""

    labels = pd.read_csv(f"{path}.csv", index_col=0)

    labels["data"] = labels["label"].apply(
        lambda i: [
            pd.read_csv(path / f"{i}_t{t}.csv", index_col=0) for t in [1, 2]
        ]
    )
    return labels


def reshape_dataset(loaded):
    """Reshape list of input data into two dataframes with each sample data in
    rows."""
    t1_data = loaded["data"].apply(
        lambda x: pd.Series(
            np.reshape(
                x[0].values if isinstance(x[0], pd.DataFrame) else x[0], -1
            )
        )
    )
    t2_data = loaded["data"].apply(
        lambda x: pd.Series(
            np.reshape(
                x[1].values if isinstance(x[0], pd.DataFrame) else x[0], -1
            )
        )
    )
    return t1_data, t2_data, loaded["group"]


def reshape_dataset_2d(dataset, m=10, n=10):
    """Reshape dataset into numpy matrix."""

    t1_data = dataset["data"].apply(
        lambda t: np.reshape(
            t[0].values if isinstance(t[0], pd.DataFrame) else t[0], (m, n, -1)
        )
    )
    t2_data = dataset["data"].apply(
        lambda t: np.reshape(
            t[1].values if isinstance(t[1], pd.DataFrame) else t[1], (m, n, -1)
        )
    )

    return np.stack(t1_data), np.stack(t2_data), dataset["group"]


def decomposition(dataset):
    """Non-linear decompositions of the data for visualization purposes."""
    t1, t2, y = reshape_dataset(dataset)
    # use a mds model first
    model = manifold.MDS()
    tf1 = model.fit_transform(t1, y)

    model = manifold.MDS()
    tf2 = model.fit_transform(t2, y)

    return tf1, tf2, y


def identity_block(input_tensor, kernel_size, filters, stage, block, tnum=0):
    """The identity block is the block that has no conv layer at shortcut.
    # Arguments
        input_tensor: input tensor
        kernel_size: default 3, the kernel size of
            middle conv layer at main path
        filters: list of integers, the filters of 3 conv layer at main path
        stage: integer, current stage label, used for generating layer names
        block: 'a','b'..., current block label, used for generating layer names
    # Returns
        Output tensor for the block.
    """
    filters1, filters2, filters3 = filters
    bn_axis = 3
    conv_name_base = f'{tnum}_res' + str(stage) + block + '_branch'
    bn_name_base = f'{tnum}_bn' + str(stage) + block + '_branch'

    x = layers.Conv2D(filters1, (1, 1),
                      kernel_initializer='he_normal',
                      name=conv_name_base + '2a')(input_tensor)
    x = layers.BatchNormalization(axis=bn_axis, name=bn_name_base + '2a')(x)
    x = layers.Activation('relu')(x)

    x = layers.Conv2D(filters2, kernel_size,
                      padding='same',
                      kernel_initializer='he_normal',
                      name=conv_name_base + '2b')(x)
    x = layers.BatchNormalization(axis=bn_axis, name=bn_name_base + '2b')(x)
    x = layers.Activation('relu')(x)

    x = layers.Conv2D(filters3, (1, 1),
                      kernel_initializer='he_normal',
                      name=conv_name_base + '2c')(x)
    x = layers.BatchNormalization(axis=bn_axis, name=bn_name_base + '2c')(x)

    x = layers.add([x, input_tensor])
    x = layers.Activation('relu')(x)
    return x


def conv_block(input_tensor,
               kernel_size,
               filters,
               stage,
               block,
               tnum=0,
               strides=(2, 2)):
    """A block that has a conv layer at shortcut.
    # Arguments
        input_tensor: input tensor
        kernel_size: default 3, the kernel size of
            middle conv layer at main path
        filters: list of integers, the filters of 3 conv layer at main path
        stage: integer, current stage label, used for generating layer names
        block: 'a','b'..., current block label, used for generating layer names
        strides: Strides for the first conv layer in the block.
    # Returns
        Output tensor for the block.
    Note that from stage 3,
    the first conv layer at main path is with strides=(2, 2)
    And the shortcut should have strides=(2, 2) as well
    """
    filters1, filters2, filters3 = filters
    bn_axis = 3
    conv_name_base = f'{tnum}_res' + str(stage) + block + '_branch'
    bn_name_base = f'{tnum}_bn' + str(stage) + block + '_branch'

    x = layers.Conv2D(filters1, (1, 1), strides=strides,
                      kernel_initializer='he_normal',
                      name=conv_name_base + '2a')(input_tensor)
    x = layers.BatchNormalization(axis=bn_axis, name=bn_name_base + '2a')(x)
    x = layers.Activation('relu')(x)

    x = layers.Conv2D(filters2, kernel_size, padding='same',
                      kernel_initializer='he_normal',
                      name=conv_name_base + '2b')(x)
    x = layers.BatchNormalization(axis=bn_axis, name=bn_name_base + '2b')(x)
    x = layers.Activation('relu')(x)

    x = layers.Conv2D(filters3, (1, 1),
                      kernel_initializer='he_normal',
                      name=conv_name_base + '2c')(x)
    x = layers.BatchNormalization(axis=bn_axis, name=bn_name_base + '2c')(x)

    shortcut = layers.Conv2D(filters3, (1, 1), strides=strides,
                             kernel_initializer='he_normal',
                             name=conv_name_base + '1')(input_tensor)
    shortcut = layers.BatchNormalization(
        axis=bn_axis, name=bn_name_base + '1')(shortcut)

    x = layers.add([x, shortcut])
    x = layers.Activation('relu')(x)
    return x


def create_resnet(xshape, yshape, num_inputs=2, classweights=None):
    """Create resnet."""
    inputs = []
    input_ends = []

    for num in range(num_inputs):
        i = layers.Input(shape=xshape)
        inputs.append(i)
        x = i

        # x = layers.Conv2D(
        #     64, (5, 5),
        #     strides=(2, 2), padding="valid", kernel_initializer="he_normal",
        #     name="conv1")(x)
        # x = layers.BatchNormalization(axis=3)(x)
        # x = layers.Activation("relu")(x)
        # x = layers.ZeroPadding2D(padding=(1, 1))(x)
        # x = layers.MaxPooling2D((3, 3), strides=(2, 2))(x)

        x = conv_block(x, 3, [32, 32, 128], stage=2, block='a', strides=(1, 1), tnum=num)
        x = identity_block(x, 3, [32, 32, 128], stage=2, block='b', tnum=num)
        x = identity_block(x, 3, [32, 32, 128], stage=2, block='c', tnum=num)

        x = conv_block(x, 3, [64, 64, 256], stage=3, block='a', tnum=num)
        x = identity_block(x, 3, [64, 64, 256], stage=3, block='b', tnum=num)
        x = identity_block(x, 3, [64, 64, 256], stage=3, block='c', tnum=num)
        x = identity_block(x, 3, [64, 64, 256], stage=3, block='d', tnum=num)

        x = conv_block(x, 3, [128, 128, 512], stage=4, block='a', tnum=num)
        x = identity_block(x, 3, [128, 128, 512], stage=4, block='b', tnum=num)
        x = identity_block(x, 3, [128, 128, 512], stage=4, block='c', tnum=num)
        x = identity_block(x, 3, [128, 128, 512], stage=4, block='d', tnum=num)
        x = identity_block(x, 3, [128, 128, 512], stage=4, block='e', tnum=num)
        x = identity_block(x, 3, [128, 128, 512], stage=4, block='f', tnum=num)

        x = conv_block(x, 3, [256, 256, 1024], stage=5, block='a', tnum=num)
        x = identity_block(x, 3, [256, 256, 1024], stage=5, block='b', tnum=num)
        x = identity_block(x, 3, [256, 256, 1024], stage=5, block='c', tnum=num)

        x = layers.GlobalAveragePooling2D(name=f'{num}_avg_pool')(x)
        input_ends.append(x)

    x = layers.concatenate(input_ends)
    x = layers.Dense(yshape, activation='softmax')(x)

    model = models.Model(inputs=inputs, outputs=x)

    lossfun = "categorical_crossentropy"
    model.compile(
        loss=lossfun,
        optimizer=optimizers.Adam(
            lr=0.0001, decay=0.0, epsilon=0.1
        ),
        metrics=["acc"]
    )
    return model


def create_model_convolutional(
        xshape, yshape, num_inputs=2
):
    """Create a convnet model. The data will be feeded as a 3d matrix."""
    inputs = []
    input_ends = []
    for i in range(num_inputs):
        t_input = layers.Input(shape=xshape)

        x = t_input
        x = layers.Conv2D(filters=32, kernel_size=2, activation="relu", strides=1)(x)
        x = layers.Conv2D(filters=64, kernel_size=2, activation="relu", strides=2)(x)
        x = layers.MaxPooling2D(pool_size=2, strides=2)(x)
        x = layers.BatchNormalization()(x)
        x = layers.Dropout(0.2)(x)

        x = layers.Conv2D(filters=64, kernel_size=2, activation="relu", strides=1)(x)
        x = layers.GlobalMaxPooling2D()(x)
        x = layers.BatchNormalization()(x)
        x = layers.Dropout(0.2)(x)

        # x = layers.Flatten()(x)

        input_ends.append(x)
        inputs.append(t_input)

    x = layers.concatenate(input_ends)

    x = layers.Dense(
        units=256, activation="relu", kernel_initializer="uniform",
        kernel_regularizer=regularizers.l2(0.001)
    )(x)
    x = layers.BatchNormalization()(x)
    x = layers.Dropout(0.2)(x)
    x = layers.Dense(
        units=128, activation="relu", kernel_initializer="uniform",
        kernel_regularizer=regularizers.l2(0.001)
    )(x)
    x = layers.BatchNormalization()(x)
    x = layers.Dropout(0.2)(x)

    final = layers.Dense(
        units=yshape, activation="softmax"
    )(x)

    model = models.Model(inputs=inputs, outputs=final)

    return model


def create_model(xshape, yshape, num_inputs=2, classweights=None):
    """Create a simple sequential neural network with multiple inputs."""

    inputs = []
    input_ends = []
    for i in range(num_inputs):
        t_input = layers.Input(shape=xshape)

        # t_attention = layers.Dense(
        #     units=xshape[0], activation="softmax",
        #     kernel_regularizer=regularizers.l2(.01)
        # )(t_input)
        # t_multatt = layers.multiply([t_input, t_attention])

        t_a = layers.Dense(
            units=128, activation="relu", kernel_initializer="uniform",
            # kernel_regularizer=regularizers.l1(.01)
        )(t_input)
        t_ad = layers.Dropout(rate=0.01)(t_a)

        t_b = layers.Dense(
            units=64, activation="relu", kernel_initializer="uniform",
            kernel_regularizer=regularizers.l1(.01)
        )(t_ad)
        t_bd = layers.Dropout(rate=0.01)(t_b)

        t_end = layers.BatchNormalization(
        )(t_b)

        input_ends.append(t_end)
        inputs.append(t_input)

    # t1_a = layers.Dense(
    #     units=128, activation="relu", kernel_initializer="uniform"
    # )(t1input)
    # t1_end = layers.Dense(
    #     units=64, activation="relu", kernel_initializer="uniform"
    # )(t1_a)

    # t2_a = layers.Dense(
    #     units=128, activation="relu", kernel_initializer="uniform"
    # )(t2input)
    # t2_end = layers.Dense(
    #     units=64, activation="relu", kernel_initializer="uniform"
    # )(t2_a)

    concat = layers.concatenate(input_ends)

    # m_a = layers.Dense(
    #     units=256, activation="relu", kernel_initializer="uniform"
    # )(concat)
    # m_b = layers.Dense(
    #     units=128, activation="relu", kernel_initializer="uniform"
    # )(m_a)
    m_end = layers.Dense(
        units=64, activation="relu", kernel_initializer="uniform"
    )(concat)

    final = layers.Dense(
        units=yshape, activation="softmax"
    )(m_end)

    model = models.Model(inputs=inputs, outputs=final)

    if classweights is None:
        lossfun = "categorical_crossentropy"
    else:
        lossfun = weighted_crossentropy.WeightedCategoricalCrossEntropy(
            weights=classweights)

    model.compile(
        loss=lossfun,
        optimizer="adam",
        metrics=["acc"]
    )

    return model


def classify(data):
    """Extremely simple sequential neural network with two
    inputs for the 10x10x12 data
    """
    groups = list(data["group"].unique())

    train, test = model_selection.train_test_split(
        data, train_size=0.8, stratify=data["group"])

    train = pd.concat([train, test])

    tr1, tr2, ytrain = reshape_dataset(train)

    binarizer = preprocessing.LabelBinarizer()
    binarizer.fit(groups)
    ytrain_mat = binarizer.transform(ytrain)

    te1, te2, ytest = reshape_dataset(test)
    ytest_mat = binarizer.transform(ytest)

    model = naive_bayes.GaussianNB()
    model.fit(tr1, ytrain)

    model = create_model((tr1.shape[1], ), ytrain_mat.shape[1], classweights=None)
    model.fit([tr1, tr2], ytrain_mat, epochs=20, batch_size=16, validation_split=0.2)
    pred = model.predict([te1, te2], batch_size=128)
    pred = binarizer.inverse_transform(pred)

    res = model.score(te1, ytest)
    print(res)
    pred = model.predict(te1)

    print("F1: ", metrics.f1_score(ytest, pred, average="micro"))

    confusion = metrics.confusion_matrix(ytest, pred, binarizer.classes_,)
    stats = {"mcc": metrics.matthews_corrcoef(ytest, pred)}
    return stats, confusion, binarizer.classes_


def pad_matrices(matrices, pad_width=1):
    """Pad matrices."""
    padded = np.pad(matrices, pad_width=[
        (0, 0),
        (pad_width, pad_width),
        (pad_width, pad_width),
        (0, 0),
    ], mode="wrap")
    return padded


def classify_convolutional(
        data, m=10, n=10, weights=None, toroidal=False, groups=None,
        path="mll-sommaps/models", kfold=False,
):
    if groups is None:
        groups = list(data["group"].unique())

    binarizer = preprocessing.LabelBinarizer()
    binarizer.fit(groups)

    # train, test = model_selection.train_test_split(data, train_size=0.9)
    confusions = []
    stats = {"mcc": []}
    test_data = data.groupby("group", as_index=False).apply(lambda d: d.sample(n=60))
    test_index = np.random.permutation(test_data.index.get_level_values(1).values)
    train_index = np.random.permutation(data.drop(test_index).index.values)
    # kf = model_selection.StratifiedKFold(n_splits=5, shuffle=True, random_state=0)
    # for i, (train_index, test_index) in enumerate(kf.split(data, data["group"])):
    for i, (train_index, test_index) in enumerate([(train_index, test_index)]):
        tr1, tr2, ytrain = reshape_dataset_2d(data.iloc[train_index, :], m=m, n=n)
        if toroidal:
            tr1 = pad_matrices(tr1, pad_width=1)
            tr2 = pad_matrices(tr2, pad_width=1)
        ytrain_mat = binarizer.transform(ytrain)

        te1, te2, ytest = reshape_dataset_2d(data.iloc[test_index, :], m=m, n=n)
        if toroidal:
            te1 = pad_matrices(te1, pad_width=1)
            te2 = pad_matrices(te2, pad_width=1)
        ytest_mat = binarizer.transform(ytest)

        model = create_model_convolutional(
            tr1[0].shape, len(groups)
        )
        if weights is None:
            lossfun = "categorical_crossentropy"
        else:
            lossfun = weighted_crossentropy.WeightedCategoricalCrossEntropy(
                weights=weights)

        model.compile(
            loss=lossfun,
            optimizer=optimizers.Adam(
                lr=0.0001, decay=0.0, epsilon=0.00001
            ),
            metrics=["acc"]
        )
        # model = create_resnet(tr1[0].shape, len(groups), classweights=weights)
        history = model.fit(
            [tr1, tr2],
            ytrain_mat,
            epochs=100,
            batch_size=128,
            callbacks=[
                # keras.callbacks.EarlyStopping(min_delta=0.01, patience=20, mode="min")
            ],
            validation_data=([te1, te2], ytest_mat),
            # class_weight={
            #     0: 1.0,  # CM
            #     1: 2.0,  # MCL
            #     2: 2.0,  # PL
            #     3: 2.0,  # LPL
            #     4: 2.0,  # MZL
            #     5: 50.0,  # FL
            #     6: 50.0,  # HCL
            #     7: 1.0,  # normal
            # }
        )
        pred_mat = model.predict([te1, te2], batch_size=128)
        pred = binarizer.inverse_transform(pred_mat)

        # save the model weights after training
        modelpath = pathlib.Path(path)
        modelpath.mkdir(parents=True, exist_ok=True)
        model.save(modelpath / f"model_{i}.h5")
        with open(str(modelpath / f"history_{i}.p"), "wb") as hfile:
            pickle.dump(history.history, hfile)
        pred_df = pd.DataFrame(
            pred_mat, columns=groups, index=data.loc[test_index, "label"])
        pred_df["correct"] = ytest.tolist()
        pred_df.to_csv(modelpath / f"predictions_{i}.csv")

        print("F1: ", metrics.f1_score(ytest, pred, average="micro"))

        confusion = metrics.confusion_matrix(ytest, pred, groups,)
        print(confusion)
        confusions.append(confusion)
        stats["mcc"].append(metrics.matthews_corrcoef(ytest, pred))
        if not kfold:
            break
    return stats, confusions, groups


def subtract_ref_data(data, references):
    data["data"] = data["data"].apply(
        lambda t: [r - a for r, a in zip(references, t)]
    )
    return data


def normalize_data(data):
    data["data"] = data["data"].apply(
        lambda t: [
            pd.DataFrame(
                preprocessing.MinMaxScaler().fit_transform(
                    preprocessing.StandardScaler().fit_transform(d)
                ),
                columns=d.columns
            ) for d in t]
    )
    return data


def remove_counts(data):
    data["data"] = data["data"].apply(
        lambda t: [d.drop("counts", axis=1) for d in t])
    return data


def sqrt_counts(data):
    def sqrt_df(df):
        if "counts" in df.columns:
            df["counts"] = np.sqrt(df["counts"])
        return df
    data["data"] = data["data"].apply(lambda t: [sqrt_df(d) for d in t])
    return data


def modify_groups(data, mapping):
    """Change the cohort composition according to the given
    cohort composition."""
    data["group"] = data["group"].apply(lambda g: mapping.get(g, g))
    return data


def confusion_f1(confusion):
    """Calculate f1 score from confusion matrix."""
    pass


def create_weight_matrix(group_map, groups, base_weight=5):
    """Generate weight matrix from given group mapping."""
    # expand mapping to all other groups if None is given
    expanded_groups = {}
    for (group_a, group_b), v in group_map.items():
        if group_a is None:
            for g in groups:
                if g != group_b:
                    expanded_groups[(g, group_b)] = v
        elif group_b is None:
            for g in groups:
                if g != group_a:
                    expanded_groups[(group_a, g)] = v
        else:
            expanded_groups[(group_a, group_b)] = v

    weights = base_weight * np.ones((len(groups), len(groups)))
    for i in range(len(groups)):
        weights[i, i] = 1
    for (group_a, group_b), (ab_err, ba_err) in expanded_groups.items():
        weights[groups.index(group_a), groups.index(group_b)] = ab_err
        weights[groups.index(group_b), groups.index(group_a)] = ba_err
    return weights


def main():
    map_size = 32

    inputpath = pathlib.Path("mll-sommaps/sample_maps/completeretrain_toroid_s32")

    indata = load_dataset(inputpath)
    indata = remove_counts(indata)
    # indata = sqrt_counts(indata)
    indata = normalize_data(indata)

    # ref_maps = [
    #     pd.read_csv(f"sommaps/reference/t{t}.csv", index_col=0)
    #     for t in [1, 2]
    # ]
    # subdata = subtract_ref_data(indata, ref_maps)

    # groups = ["CLL", "MBL", "MCL", "PL", "LPL", "MZL", "FL", "HCL", "normal"]
    # 8-class
    # groups = ["CM", "MCL", "PL", "LPL", "MZL", "FL", "HCL", "normal"]
    # group_map = {
    #     "CLL": "CM",
    #     "MBL": "CM",
    # }
    # 6-class
    groups = ["CM", "MP", "LM", "FL", "HCL", "normal"]
    group_map = {
        "CLL": "CM",
        "MBL": "CM",
        "MZL": "LM",
        "LPL": "LM",
        "MCL": "MP",
        "PL": "MP",
    }
    indata = modify_groups(indata, mapping=group_map)
    indata = indata.loc[indata["group"].isin(groups), :]
    indata.reset_index(drop=True, inplace=True)
    # Group weights are a dict mapping tuples to tuples. Weights are for
    # false classifications in the given direction.
    # (a, b) --> (a>b, b>a)
    group_weights = {
        ("normal", None): (10.0, 100.0),
        ("MBL", "CLL"): (2, 2),
        ("MZL", "LPL"): (2, 2),
        ("MCL", "PL"): (2, 2),
        ("FL", "LPL"): (3, 5),
        ("FL", "MZL"): (3, 5),
    }
    weights = create_weight_matrix(group_weights, groups, base_weight=5)
    weights = None

    # plotpath = pathlib.Path("sommaps/output/lotta")
    # tf1, tf2, y = decomposition(indata)
    # plot_transformed(plotpath, tf1, tf2, y)
    validation = "holdout"
    name = "retrain_ep100"

    # n_metrics, n_confusion, n_groups = classify(normdata)
    nmetrics, confusions, groups = classify_convolutional(
        indata, m=map_size, n=map_size, toroidal=True, weights=weights,
        kfold=False, groups=groups,
        path=f"mll-sommaps/models/{name}")
    sum_confusion = np.sum(confusions, axis=0)

    outpath = pathlib.Path(f"output/{name}_{validation}")
    outpath.mkdir(parents=True, exist_ok=True)

    plotting.plot_confusion_matrix(
        sum_confusion, groups, normalize=True,
        filename=outpath / "confusion_merged_weighted", dendroname=outpath / "dendro_merged_weighted"
    )


if __name__ == "__main__":
    main()
