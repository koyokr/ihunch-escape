from pathlib import Path
from typing import Iterable, List, Tuple, Optional, Dict

import cv2
import numpy as np
from detectron2 import model_zoo
from detectron2.config import get_cfg
from detectron2.engine import DefaultPredictor
from xgboost import XGBClassifier

from .modules.inference_engine_pytorch import InferenceEnginePyTorch
from .modules.parse_poses import parse_poses


here = Path(__file__).parent.absolute()


def normalize_keypoint(keypoint: Iterable, x_max, y_max, x_sub, y_sub) -> List[float]:
    arr = []
    for x, y, a in keypoint:
        arr.append((x - x_sub) / x_max)
        arr.append((y - y_sub) / y_max)
        arr.append(a)
    return arr


def normalize_pose_2d(pose_2d: Iterable, x_max, y_max) -> List[float]:
    arr = []
    for i, x in enumerate(pose_2d[:-1], start=1):
        i %= 3
        if i == 1:
            x /= x_max
        elif i == 2:
            x /= y_max
        arr.append(x)
    arr.append(pose_2d[-1])
    return arr


def setup_cfg(config_file: str, confidence_threshold=0.5):
    cfg = get_cfg()
    cfg.merge_from_file(model_zoo.get_config_file(config_file))
    cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = confidence_threshold
    cfg.MODEL.WEIGHTS = model_zoo.get_checkpoint_url(config_file)
    cfg.freeze()
    return cfg


class iHunchPredictor:
    __slots__ = ['keypoint_predictor', 'inference_engine', 'ihunch_predictor']

    def __init__(self,
                 keypoint_predictor_config='COCO-Keypoints/keypoint_rcnn_R_50_FPN_3x.yaml',
                 inference_engine_path='data/human-pose-estimation-3d.pth',
                 ihunch_predictor_path='data/xgb-ihunch-prediction.bin'):
        config_file = setup_cfg(keypoint_predictor_config, 0.9)
        self.keypoint_predictor = DefaultPredictor(config_file)
        self.inference_engine = InferenceEnginePyTorch(here / inference_engine_path, 'gpu')
        self.ihunch_predictor = XGBClassifier()
        self.ihunch_predictor.load_model(here / ihunch_predictor_path)

    def get_keypoint_box(self, img: np.ndarray) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        outputs = self.keypoint_predictor(img)['instances']
        if len(outputs) > 0:
            output = outputs[0].to('cpu')
            keypoint, = output.get('pred_keypoints')
            box, = output.get('pred_boxes')
            return keypoint, box
        else:
            return None, None

    def get_pose2d_pose3d(self, img: np.ndarray) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        base_height = 256
        stride = 8
        fx = np.float32(0.8 * img.shape[1])
        input_scale = base_height / img.shape[0]
        scaled_img = cv2.resize(img, dsize=None, fx=input_scale, fy=input_scale)
        scaled_img = scaled_img[:, 0:scaled_img.shape[1] - (scaled_img.shape[1] % stride)]
        inference_result = self.inference_engine.infer(scaled_img)
        poses_3d, poses_2d = parse_poses(inference_result, input_scale, stride, fx)
        if poses_2d.size > 0 and poses_3d.size > 0:
            pose2d = poses_2d[0]
            pose3d = poses_3d[0]
            return pose2d, pose3d
        else:
            return None, None

    def extract_features(self, img: np.ndarray) -> Optional[np.ndarray]:
        keypoint, box = self.get_keypoint_box(img)
        if keypoint is None:
            return None
        x1, y1, x2, y2 = box.int()
        cropped_img = img[y1:y2, x1:x2]
        pose2d, pose3d = self.get_pose2d_pose3d(cropped_img)
        if pose2d is None:
            return None
        y_max, x_max = cropped_img.shape[:2]
        keypoint = normalize_keypoint(keypoint, x_max, y_max, x1, y1)
        pose2d = normalize_pose_2d(pose2d, x_max, y_max)
        pose3d = pose3d.tolist()
        return np.asarray(keypoint + pose2d + pose3d)

    def predict(self, img_bytes: bytes) -> Dict[str, float]:
        img = np.frombuffer(img_bytes, dtype=np.uint8)
        img = cv2.imdecode(img, cv2.IMREAD_COLOR)
        features = self.extract_features(img)
        if features is None:
            return None
        x = np.asarray([features])
        pred = self.ihunch_predictor.predict_proba(x)[0][1]
        return {'pred': pred}
