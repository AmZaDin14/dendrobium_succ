from Bio import SeqIO
import numpy as np
from protlearn.features import paac
from sklearn.preprocessing import StandardScaler
import re


def extract_pse_aac_from_fasta(fasta_file, lambda_param=3, w_param=0.05):
    protein_sequences = []
    for record in SeqIO.parse(fasta_file, "fasta"):
        sequence = str(record.seq)
        sequence = re.sub(r"[UZOBX-]", "N", sequence)
        protein_sequences.append(sequence)

    paac_comp, desc = paac(protein_sequences, lambda_=lambda_param, remove_zero_cols=False)
    return np.array(paac_comp)


def GetPAAC_4(train_negative, train_positive, test_negative, test_positive):
    train_positive_embedding = extract_pse_aac_from_fasta(train_positive)
    train_negative_embedding = extract_pse_aac_from_fasta(train_negative)
    X_train = np.vstack((train_negative_embedding, train_positive_embedding))

    train_positive_labels = np.ones(train_positive_embedding.shape[0])
    train_negative_labels = np.zeros(train_negative_embedding.shape[0])
    y_train = np.concatenate((train_negative_labels, train_positive_labels), axis=0)

    test_positive_embedding = extract_pse_aac_from_fasta(test_positive)
    test_negative_embedding = extract_pse_aac_from_fasta(test_negative)
    X_test = np.vstack((test_negative_embedding, test_positive_embedding))

    test_positive_labels = np.ones(test_positive_embedding.shape[0])
    test_negative_labels = np.zeros(test_negative_embedding.shape[0])
    y_test = np.concatenate((test_negative_labels, test_positive_labels), axis=0)

    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_test = scaler.transform(X_test)
    # print(X_train.shape, y_train.shape, X_test.shape, y_test.shape)
    return X_train, y_train, X_test, y_test
