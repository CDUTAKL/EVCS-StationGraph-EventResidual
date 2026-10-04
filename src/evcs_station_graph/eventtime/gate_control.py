"""SG-EXP-027: retain gate capacity, remove node-specific gate values only."""
import torch
from torch import nn


class SharedNodeGate(nn.Module):
    def __init__(self, original):
        super().__init__()
        # Reuse the initialized modules; no additional RNG draws or dummy weights.
        self.W_r = original.W_r
        self.W_gate = original.W_gate
        self.norm = original.norm
        self.dropout = original.dropout
        if original.relation_dropout != 0:
            raise ValueError('Control requires frozen zero relation dropout')

    def forward(self, h, adj, logits):
        beta = logits.softmax(0)
        message = torch.zeros_like(h)
        for r, (a, w) in enumerate(zip(adj, self.W_r)):
            neighbor = torch.einsum('nm,bmd->bnd', a, h)
            message = message + beta[r] * w(neighbor)
        gate = self.W_gate(torch.cat((h, message), -1)).mean(1, keepdim=True).sigmoid()
        updated = gate * message + (1-gate) * h
        return self.norm(h + self.dropout(updated))
