import torch
from torch import nn

class neural_network_binary_classification(nn.Module):
    def __init__(self, units_per_layer=[2, 5, 1]):
        super().__init__()
        if len(units_per_layer) < 2:
            raise Exception("Units_per_layer should be longer than 2.")
        layers = []
        for i in range(len(units_per_layer)-1):
            layers.append(nn.Linear(units_per_layer[i], units_per_layer[i + 1]))
            if i < len(units_per_layer) - 2:
                layers.append(nn.ReLU())
                layers.append(nn.Dropout(p=0.2))
        layers.append(nn.Sigmoid())
        self.model = nn.Sequential(*layers)

    def forward(self, x):
        return self.model(x)




