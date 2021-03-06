import torch
import torch.nn as nn
import torch.nn.functional as F

from .point_net import *
from .options import Options
from .dgcnn import *
from .spidercnn import Spidercnn_seg_fullnet as spidercnn
from .graphcnn import *
from .pointconv import *
# from model.SONet.segmenter import Model as sonet
from .spidercnn import Spidercnn_seg_fullnet
# from model.pointnet2.net import Pointnet2SSG
import sys
sys.path.append("..") # Adds higher directory to python modules path.
from utils.tools import *
import numpy as np
# from model.RSCNN.rscnn import RSCNN_MSN


class PCKLoss(nn.Module):
    """
    Calculate the cross entropy between pred logits and one hot kp labels.
    """
    def __init__(self):
        super(PCKLoss, self).__init__()
        self.softmax = nn.Softmax(dim=1)

    def forward(self, pred, kps):
        pred = self.softmax(pred)
        loss = F.binary_cross_entropy(pred, kps)
        pred_kp_idx = torch.argmax(pred, dim=1)
        return loss, pred_kp_idx
    

class BenchMark(nn.Module):
    def __init__(self, cfg):
        super(BenchMark, self).__init__()
        self.num_points = cfg.num_points
        self.net = cfg.network

        self.num_kps = cfg.num_kps

        if self.net == "pointnet":
            self.backbone = PointNetDenseCls(self.num_kps, cfg=cfg)
        elif self.net == "dgcnn":
            self.backbone = DGCNN(self.num_kps, cfg=cfg)
        elif self.net == "pointconv":
            self.backbone = PointConvDensityClsSsg(self.num_kps)
        elif self.net == "graphcnn":
            self.backbone = GraphConvNet([3, 1024, 5, 1024, 5], [512, self.num_kps])
            
        elif self.net == "spidercnn":
            self.backbone = Spidercnn_seg_fullnet(self.num_kps)
        elif self.net == "rscnn":
            from .RSCNN.rscnn import RSCNN_MSN
            self.backbone = RSCNN_MSN(self.num_kps)

    def forward(self, input_):
        pcd = input_[0]
        pcd = pcd.cuda()
        logits = self.backbone(pcd.transpose(1, 2).cuda())
        return logits

class BenchMarkLoss(nn.Module):
    def __init__(self, cfg):
        super(BenchMarkLoss, self).__init__()
        self.pck_criterion = PCKLoss()
        self.cfg = cfg

    def forward(self, input_var):
        loss = {}
        pred, kps = input_var
        kps_one_hot = convert_kp_to_one_hot(kps, pred.size(1))
        loss_pck, pred_kps = self.pck_criterion(pred, kps_one_hot.cuda())
        loss["total"] = loss_pck
        return loss


class BenchMarkMetric(nn.Module):
    def __init__(self, cfg):
        super(BenchMarkMetric, self).__init__()
        self.num_kps = cfg.num_kps

    def forward(self, input):
        pts, gt_index, pred_index = input
        pts = pts.cpu().numpy()
        gt_index = gt_index.cpu().numpy().astype(np.int32)
        pred_index = pred_index.cpu().numpy().astype(np.int32)
        dist_info = pck(pts, gt_index, pred_index)
        corr_list = calculate_correspondence(dist_info, gt_index)
        return np.array(corr_list)

