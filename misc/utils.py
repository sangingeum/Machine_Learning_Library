import numpy
import torch
import multiprocessing
from torch.utils.data import DataLoader, TensorDataset
from sklearn.model_selection import train_test_split
from data_preprocessing.class_weighting import *
from torch import nn
import numpy as np
import torch.utils.data as data
from sklearn.metrics import accuracy_score

def calculate_loss(model, device, loss_function, test_data_loader, calculate_accuracy=True, X_on_the_fly_function=None):
    model.eval()
    with torch.inference_mode():
        average_test_loss = 0
        correct = 0
        accuracy = None
        if calculate_accuracy:
            for test_data in test_data_loader:
                test_X, test_y = test_data
                if X_on_the_fly_function is not None:
                    test_X = X_on_the_fly_function(test_X)
                test_X = test_X.to(device)
                test_y = test_y.to(device)
                test_y_prediction = model(test_X)
                test_loss = loss_function(test_y_prediction, test_y)
                if test_y.shape != test_y_prediction.shape:
                    test_y_prediction = torch.argmax(test_y_prediction, dim=1)
                else:
                    test_y_prediction = torch.round(test_y_prediction)
                correct += accuracy_score(test_y.cpu(), test_y_prediction.cpu(), normalize=False)
                average_test_loss += test_loss
            accuracy = correct / len(test_data_loader.dataset)
        else:
            for test_data in test_data_loader:
                test_X, test_y = test_data
                if X_on_the_fly_function is not None:
                    test_X = X_on_the_fly_function(test_X)
                test_X = test_X.to(device)
                test_y = test_y.to(device)
                test_y_prediction = model(test_X)
                test_loss = loss_function(test_y_prediction, test_y)
                average_test_loss += test_loss

        average_test_loss /= len(test_data_loader.dataset)

    return average_test_loss, accuracy


def train_loop(train_data_set, test_data_set, epochs, model, device, batch_size, loss_function, optimizer,
               print_interval, weighted_sample=False, calculate_accuracy=False, X_on_the_fly_function=None,
               collate_fn=torch.utils.data.default_collate, test_first=False, drop_last=False):

    # create data loader
    if weighted_sample:
        if isinstance(train_data_set, data.dataset.TensorDataset):
            train_sampler = get_weighted_sampler(train_data_set.tensors[1])
        elif torch.is_tensor(train_data_set.targets):
            train_sampler = get_weighted_sampler(train_data_set.targets)
        else:
            train_sampler = get_weighted_sampler(torch.tensor(train_data_set.targets))

        train_data_loader = DataLoader(train_data_set, batch_size=batch_size, sampler=train_sampler, collate_fn=collate_fn, drop_last=drop_last)
        test_data_loader = DataLoader(test_data_set, batch_size=batch_size, shuffle=True, collate_fn=collate_fn, drop_last=drop_last)
    else:
        train_data_loader = DataLoader(train_data_set, batch_size=batch_size, shuffle=True, collate_fn=collate_fn, drop_last=drop_last)
        test_data_loader = DataLoader(test_data_set, batch_size=batch_size, shuffle=True, collate_fn=collate_fn, drop_last=drop_last)

    if test_first:
        print_progress(train_data_loader, test_data_loader, model, device, 0, loss_function, 0, calculate_accuracy, X_on_the_fly_function)
    for epoch in range(1, epochs+1):
        average_train_loss = 0
        for train_data in train_data_loader:
            model.train()
            X, y = train_data
            if X_on_the_fly_function is not None:
                X = X_on_the_fly_function(X)
            X = X.to(device)
            y = y.to(device)

            y_prediction = model(X)

            loss = loss_function(y_prediction, y)
            average_train_loss += loss
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

        if print_interval <= 0:
            continue
        if epoch % print_interval == 0:
            print_progress(train_data_loader, test_data_loader, model, device, epoch, loss_function, average_train_loss, calculate_accuracy, X_on_the_fly_function)


def train_loop_with_adjacency_matrix(train_data_set, test_data_set, features, labels,
                                     epochs, model, device, batch_size, loss_function, optimizer,
                                     print_interval, adjacency_matrix):

    train_data_loader = DataLoader(train_data_set, batch_size=batch_size, shuffle=True, drop_last=False)
    test_data_loader = DataLoader(test_data_set, batch_size=batch_size, shuffle=True, drop_last=False)
    # train loop
    adjacency_matrix = adjacency_matrix.to(device)
    features = features.to(device)
    labels = labels.to(device)
    for epoch in range(1, epochs + 1):
        average_train_loss = 0
        for train_data in train_data_loader:
            model.train()
            i = train_data
            y_prediction = model(features, adjacency_matrix)
            loss = loss_function(y_prediction[i], labels[i])
            average_train_loss += loss
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

        if print_interval <= 0:
            continue
        if epoch % print_interval == 0:
            average_test_loss = 0
            correct = 0
            model.eval()
            with torch.inference_mode():
                for test_data in test_data_loader:
                    i = test_data
                    y_prediction = model(features, adjacency_matrix)
                    loss = loss_function(y_prediction[i], labels[i])
                    correct += accuracy_score(y_true=labels[i].cpu(), y_pred=torch.round(y_prediction[i]).cpu(), normalize=False)
                    average_test_loss += loss

                average_train_loss /= len(train_data_loader.dataset)
                average_test_loss /= len(test_data_loader.dataset)
                print("epoch: {}, train loss:{}, test loss: {}, acc: {}".format(epoch, average_train_loss, average_test_loss,
                                                                     correct / len(test_data_loader.dataset)))


def print_progress(train_data_loader, test_data_loader, model, device, epoch, loss_function, average_train_loss, calculate_accuracy, X_on_the_fly_function=None):
    average_train_loss /= len(train_data_loader.dataset)
    average_test_loss, accuracy = calculate_loss(model, device, loss_function, test_data_loader,  calculate_accuracy=calculate_accuracy, X_on_the_fly_function=X_on_the_fly_function)
    print_learning_progress(epoch, average_train_loss, average_test_loss, accuracy)


def print_learning_progress(epoch, train_loss, test_loss, accuracy=None):
    progress_string = "\nepoch: {}"\
                      "\ntrain loss: {}"\
                      "\ntest loss : {}".format(epoch, train_loss, test_loss)
    if accuracy is not None:
        progress_string += "\naccuracy: {}".format(accuracy)
    print(progress_string)

def print_class_distribution(y: numpy.array, is_one_hot=False):
    if is_one_hot:
        counts = np.sum(y, axis=0)
        unique = list(range(len(y[0])))
    else:
        unique, counts = np.unique(y, return_counts=True)
    class_distribution = dict(zip(unique, counts))
    print(class_distribution)
    return class_distribution

def get_device_name_agnostic():
    return "cuda" if torch.cuda.is_available() else "cpu"

def get_cpu_count():
    return multiprocessing.cpu_count()

def calculate_height_width_after_conv2d(height, width, kernel_size, stride=1, padding=0, dilation=1):
    out_height = np.floor((height + 2 * padding - dilation * (kernel_size - 1) - 1) / stride + 1)
    out_width = np.floor((width + 2 * padding - dilation * (kernel_size - 1) - 1) / stride + 1)
    return int(out_height), int(out_width)

def calculate_height_width_after_max_pool_2d(height, width, kernel_size, stride=1, padding=0, dilation=1):
    out_height = np.floor((height + 2 * padding - dilation * (kernel_size - 1) - 1) / stride + 1)
    out_width = np.floor((width + 2 * padding - dilation * (kernel_size - 1) - 1) / stride + 1)
    return int(out_height), int(out_width)
