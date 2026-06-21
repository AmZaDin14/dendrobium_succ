from Bio import SeqIO
import numpy as np
from protlearn.features import cksaap
from sklearn.preprocessing import StandardScaler
import re


def extract_cksAAP_from_fasta(fasta_file):
    protein_sequences = []
    for record in SeqIO.parse(fasta_file, "fasta"):
        sequence = str(record.seq)
        sequence = re.sub(r"[UZOBX-]", "N", sequence)
        protein_sequences.append(sequence)

    ck, pairs = cksaap(protein_sequences, remove_zero_cols=False)
    return ck


def GetCKSAAP_2(negative, positive):
    positive_embedding = extract_cksAAP_from_fasta(positive)
    negative_embedding = extract_cksAAP_from_fasta(negative)
    X = np.vstack((positive_embedding, negative_embedding))

    num_P = positive_embedding.shape[0]
    num_N = negative_embedding.shape[0]
    ratio = num_P / num_N if num_P > num_N else num_N / num_P

    positive_labels = np.ones(num_P)
    negative_labels = np.zeros(num_N)
    y = np.concatenate((positive_labels, negative_labels), axis=0)
    # print(X.shape, y.shape)
    return X, y, float(ratio)


def GetCKSAAP_4(train_negative, train_positive, test_negative, test_positive):
    train_positive_embedding = extract_cksAAP_from_fasta(train_positive)
    train_negative_embedding = extract_cksAAP_from_fasta(train_negative)
    X_train = np.vstack((train_negative_embedding, train_positive_embedding))

    num_train_P = train_positive_embedding.shape[0]
    num_train_N = train_negative_embedding.shape[0]
    train_positive_labels = np.ones(num_train_P)
    train_negative_labels = np.zeros(num_train_N)
    y_train = np.concatenate((train_negative_labels, train_positive_labels), axis=0)

    test_positive_embedding = extract_cksAAP_from_fasta(test_positive)
    test_negative_embedding = extract_cksAAP_from_fasta(test_negative)
    X_test = np.vstack((test_negative_embedding, test_positive_embedding))

    num_test_P = test_positive_embedding.shape[0]
    num_test_N = test_negative_embedding.shape[0]
    test_positive_labels = np.ones(num_test_P)
    test_negative_labels = np.zeros(num_test_N)
    y_test = np.concatenate((test_negative_labels, test_positive_labels), axis=0)

    num_P = num_train_P + num_test_P
    num_N = num_train_N + num_test_N
    ratio = num_P / num_N if num_P > num_N else num_N / num_P

    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_test = scaler.transform(X_test)
    # print(X_train.shape, y_train.shape, X_test.shape, y_test.shape)
    return X_train, y_train, X_test, y_test, float(ratio)


def GetCKSAAP_41(train_negative, train_positive, test_negative, test_positive):
    train_positive_embedding = extract_cksAAP_from_fasta(train_positive)
    train_negative_embedding = extract_cksAAP_from_fasta(train_negative)
    X_train = np.vstack((train_negative_embedding, train_positive_embedding))

    num_train_P = train_positive_embedding.shape[0]
    num_train_N = train_negative_embedding.shape[0]
    train_positive_labels = np.ones(num_train_P)
    train_negative_labels = np.zeros(num_train_N)
    y_train = np.concatenate((train_negative_labels, train_positive_labels), axis=0)

    test_positive_embedding = extract_cksAAP_from_fasta(test_positive)
    test_negative_embedding = extract_cksAAP_from_fasta(test_negative)
    X_test = np.vstack((test_negative_embedding, test_positive_embedding))

    num_test_P = test_positive_embedding.shape[0]
    num_test_N = test_negative_embedding.shape[0]
    test_positive_labels = np.ones(num_test_P)
    test_negative_labels = np.zeros(num_test_N)
    y_test = np.concatenate((test_negative_labels, test_positive_labels), axis=0)

    num_P = num_train_P + num_test_P
    num_N = num_train_N + num_test_N
    ratio = num_P / num_N if num_P > num_N else num_N / num_P

    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_test = scaler.transform(X_test)
    # print(X_train.shape, y_train.shape, X_test.shape, y_test.shape)
    return X_train, y_train, X_test, y_test
