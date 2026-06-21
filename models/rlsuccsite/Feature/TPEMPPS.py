from Bio import SeqIO
import numpy as np
from sklearn.preprocessing import StandardScaler
import re

weight = 21.0


# 读取FASTA文件中的所有序列
def read_fasta(fasta_file):
    sequences = []
    for seq_record in SeqIO.parse(fasta_file, "fasta"):
        sequences.append(str(seq_record.seq))
    return sequences, len(str(seq_record.seq))


# 将蛋白质序列整数化
def integerize_sequence(protein_sequence):
    # 定义一个包含所有氨基酸的字母表
    amino_acids = 'ACDEFGHIKLMNPQRSTVWXY'
    # 定义一个映射字典，将氨基酸映射到整数
    aa_to_int = {aa: i for i, aa in enumerate(amino_acids)}
    # 将U、Z、O、B替换为X
    protein_sequence = re.sub(r"[UZOB-]", "X", protein_sequence)
    # 将蛋白质序列整数化
    integer_sequence = [float(aa_to_int[aa]) for aa in protein_sequence]
    return integer_sequence


def ZccF_Int(fasta_file):
    sequences, w = read_fasta(fasta_file)
    # 整数化所有蛋白质序列
    all_integer_sequences = [integerize_sequence(sequence) for sequence in sequences]
    feature_int = np.array(all_integer_sequences)
    return feature_int


# 理化性质
def encode_protein_sequence(protein_sequence):
    protein_sequence = re.sub(r"[UZOB-]", "X", protein_sequence)
    # 疏水性
    encoding1 = {'A': 1.8, 'C': 2.5, 'D': -3.5, 'E': -3.5, 'F': 2.8, 'G': -0.4, 'H': -3.2, 'I': 4.5, 'K': -3.9,
                 'L': 3.8, 'M': 1.9, 'N': -3.5, 'P': -1.6, 'Q': -3.5, 'R': -4.5, 'S': -0.8, 'T': -0.7, 'V': 4.2,
                 'W': -0.9, 'X': 0.0, 'Y': -1.3}
    # 等电点值
    encoding2 = {'A': 6.01, 'C': 5.07, 'D': 2.77, 'E': 3.22, 'F': 5.48, 'G': 5.97, 'H': 7.59, 'I': 6.02, 'K': 9.74,
                 'L': 5.98, 'M': 5.74, 'N': 5.41, 'P': 6.30, 'Q': 5.65, 'R': 10.76, 'S': 5.68, 'T': 15.60, 'V': 5.96,
                 'W': 5.89, 'X': 0.0, 'Y': 5.66}

    encoded_sequence1 = [encoding1[aa] for aa in protein_sequence]
    encoded_sequence1 = np.array(encoded_sequence1)
    encoded_sequence2 = [encoding2[aa] for aa in protein_sequence]
    encoded_sequence2 = np.array(encoded_sequence2)

    encoded_sequences = np.vstack((encoded_sequence1, encoded_sequence2))
    return encoded_sequences


def ZccF_LiHua(fasta_file):
    sequences, window_size = read_fasta(fasta_file)
    all_features_ZccF_LiHua = []

    bof = np.array(list(range(1, int(window_size / 2 + 1))) + [int(window_size / 2 + 1)] + list(
        range(int(window_size / 2), 0, -1)), dtype=float)
    dig = np.array(list(range(int(window_size / 2 + 1), 1, -1)) + [1] + list(range(2, int(window_size / 2 + 2))),
                   dtype=float)

    for sequence in sequences:
        features_ZccF_LiHua = []
        IntFeature = np.array(integerize_sequence(sequence))
        features_ZccF_LiHua.extend(IntFeature)
        featureAdd = IntFeature
        LiHuaFeature = encode_protein_sequence(sequence)
        for feature in LiHuaFeature:
            featureAdd += IntFeature * feature
            features_ZccF_LiHua.extend(IntFeature * feature)
            features_ZccF_LiHua.extend(IntFeature * feature * bof)
            features_ZccF_LiHua.extend(IntFeature * feature * dig)

        features_ZccF_LiHua.extend(IntFeature * featureAdd)
        features_ZccF_LiHua.extend(IntFeature * featureAdd * bof)
        features_ZccF_LiHua.extend(IntFeature * featureAdd * dig)
        all_features_ZccF_LiHua.append(features_ZccF_LiHua)
    return np.array(all_features_ZccF_LiHua)


def ZccF_alltoK(fasta_file):
    sequences, window_size = read_fasta(fasta_file)
    all_features_ZccF_alltoK = []
    bof = np.array(list(range(1, int(window_size / 2 + 1))) + [int(window_size / 2 + 1)] + list(
        range(int(window_size / 2), 0, -1)), dtype=float)
    dig = np.array(list(range(int(window_size / 2 + 1), 1, -1)) + [1] + list(range(2, int(window_size / 2 + 2))),
                   dtype=float)
    for sequence in sequences:
        IntFeature = np.array(integerize_sequence(sequence))
        LiHuaFeature = encode_protein_sequence(sequence)
        features_ZccF_alltoK = []
        for feature in LiHuaFeature:
            feature_ZccF_alltoK = []
            for i in range(len(feature)):
                if i != int(window_size / 2):
                    feature_ZccF_alltoK.append(
                        IntFeature[int(window_size / 2)] + IntFeature[i] +
                        weight * (feature[int(window_size / 2)] + feature[i])
                    )
                else:
                    feature_ZccF_alltoK.append(
                        2 * (IntFeature[i] + weight * feature[i])
                    )

            features_ZccF_alltoK.extend(feature_ZccF_alltoK)
            features_ZccF_alltoK.extend(feature_ZccF_alltoK * bof)
            features_ZccF_alltoK.extend(feature_ZccF_alltoK * dig)
        all_features_ZccF_alltoK.append(features_ZccF_alltoK)
    return np.array(all_features_ZccF_alltoK)


def GetZccF_LiHua(train_negative, train_positive, test_negative, test_positive):
    train_positive_ZccF_LiHua = ZccF_LiHua(train_positive)
    train_negative_ZccF_LiHua = ZccF_LiHua(train_negative)

    X_train = np.concatenate((train_negative_ZccF_LiHua, train_positive_ZccF_LiHua), axis=0)

    N_train_Pos = train_positive_ZccF_LiHua.shape[0]
    N_train_Neg = train_negative_ZccF_LiHua.shape[0]

    train_positive_labels = np.ones(N_train_Pos)
    train_negative_labels = np.zeros(N_train_Neg)
    y_train = np.concatenate((train_negative_labels, train_positive_labels), axis=0)

    test_positive_ZccF_LiHua = ZccF_LiHua(test_positive)
    test_negative_ZccF_LiHua = ZccF_LiHua(test_negative)

    X_test = np.concatenate((test_negative_ZccF_LiHua, test_positive_ZccF_LiHua), axis=0)

    N_test_Pos = test_positive_ZccF_LiHua.shape[0]
    N_test_Neg = test_negative_ZccF_LiHua.shape[0]
    # 标签
    test_positive_labels = np.ones(N_test_Pos)
    test_negative_labels = np.zeros(N_test_Neg)
    y_test = np.concatenate((test_negative_labels, test_positive_labels), axis=0)

    num_P = N_train_Pos + N_test_Pos
    num_N = N_train_Neg + N_test_Neg
    ratio = num_P / num_N if num_P > num_N else num_N / num_P
    # print(X_train.shape, y_train.shape, X_test.shape, y_test.shape)
    return X_train, y_train, X_test, y_test, round(ratio, 2)


def GetZccF_alltoK(train_negative, train_positive, test_negative, test_positive):
    train_positive_ZccF_alltoK = ZccF_alltoK(train_positive)
    train_negative_ZccF_alltoK = ZccF_alltoK(train_negative)

    X_train = np.concatenate((train_negative_ZccF_alltoK, train_positive_ZccF_alltoK), axis=0)

    N_train_Pos = train_positive_ZccF_alltoK.shape[0]
    N_train_Neg = train_negative_ZccF_alltoK.shape[0]

    train_positive_labels = np.ones(N_train_Pos)
    train_negative_labels = np.zeros(N_train_Neg)
    y_train = np.concatenate((train_negative_labels, train_positive_labels), axis=0)

    test_positive_ZccF_alltoK = ZccF_alltoK(test_positive)
    test_negative_ZccF_alltoK = ZccF_alltoK(test_negative)

    X_test = np.concatenate((test_negative_ZccF_alltoK, test_positive_ZccF_alltoK), axis=0)

    N_test_Pos = test_positive_ZccF_alltoK.shape[0]
    N_test_Neg = test_negative_ZccF_alltoK.shape[0]

    test_positive_labels = np.ones(N_test_Pos)
    test_negative_labels = np.zeros(N_test_Neg)
    y_test = np.concatenate((test_negative_labels, test_positive_labels), axis=0)

    num_P = N_train_Pos + N_test_Pos
    num_N = N_train_Neg + N_test_Neg
    ratio = num_P / num_N if num_P > num_N else num_N / num_P
    # print(X_train.shape, y_train.shape, X_test.shape, y_test.shape)
    return X_train, y_train, X_test, y_test, round(ratio, 2)


def GetTPEMPPS(train_negative, train_positive, test_negative, test_positive):
    X_train1, y_train, X_test1, y_test, ratio = GetZccF_LiHua(train_negative, train_positive, test_negative,
                                                              test_positive)
    X_train2, y_train, X_test2, y_test, ratio = GetZccF_alltoK(train_negative, train_positive, test_negative,
                                                               test_positive)

    X_train = np.concatenate((X_train1, X_train2), axis=1)
    X_test = np.concatenate((X_test1, X_test2), axis=1)

    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_test = scaler.transform(X_test)

    print(X_train.shape, y_train.shape, X_test.shape, y_test.shape)
    return X_train, y_train, X_test, y_test, ratio