# python /project/ev_sdk/src/ji.py

import json
import os
import os.path as osp
import mmcv
import glob
import cv2
import numpy as np

from mmocr.apis import init_detector, model_inference
from mmocr.utils import list_from_file, list_to_file

from signboard_infer.ocr_pipiline import OCR_Pipeline

'''ev_sdk输出json样例
{
"model_data": {
    "objects": [
        {
            "points": [
                294,
                98,
                335,
                91,
                339,
                115,
                298,
                122
            ],
            "name": "店面招牌",
            "confidence": 0.9977550506591797
        },
        {
            "points": [
                237,
                111,
                277,
                106,
                280,
                127,
                240,
                133
            ],
            "name": "文字识别",
            "confidence": 0.9727065563201904
        }
    ]
    }
}
'''

def init(det_config="/project/ev_sdk/mmocr/configs/textdet/dbnetpp/dbnetpp_r50dcnv2_fpnc_100e_signboard.py",
        det_checkpoint="/project/train/models/dbnetpp_epoch_100.pth",
        rcg_config="/project/ev_sdk/mmocr/configs/textrecog/abinet/abinet_vision_only_signboard.py",
        rcg_checkpoint="/project/train/models/abinet_epoch_150.pth",
        device="cuda:0"):  # 模型初始化
    
    det_model = init_detector(det_config, det_checkpoint, device=device)
    if hasattr(det_model, 'module'):
        det_model = det_model.module

    rcg_model = init_detector(rcg_config, rcg_checkpoint, device=device)
    if hasattr(rcg_model, 'module'):
        rcg_model = rcg_model.module

    # build the overall model, i.e., detector + recognizer
    model = OCR_Pipeline(det_model=det_model, rcg_model=rcg_model)
    
    return model


def process_image(net, input_image, out_dir=None, args=None):
    # mmocr 暂时只能从图片读，所以这里先临时保存到图片
    if isinstance(input_image, np.ndarray):
        cv2.imwrite("/tmp/mmocr_tmp_input.png", input_image)
        input_path = "/tmp/mmocr_tmp_input.png"
    else:
        input_path = input_image

    ocr_res, ocr_res_vis_img = net.processing_img(input_path=input_path, pp_visulize = False)

    # ========== 输出到文件 ==========
    if out_dir is not None:
        assert ocr_res_vis_img is not None, "pp_visulize should be specified as True."
        img_name = os.path.basename(input_path)
        out_vis_dir = os.path.join(out_dir, 'out_vis_dir')
        mmcv.mkdir_or_exist(out_vis_dir)
        mmcv.imwrite(ocr_res_vis_img, osp.join(out_dir, img_name))
        # print(f'\nInference done, and results saved in {out_dir}\n')


    # 包装成一个字典返回
    '''
        此示例 dets 数据为
        dets = [
            [294, 98, 335, 91, 339, 115, 298, 122, 0.9827, '店面招牌'], 
            [237, 111, 277, 106, 280, 127, 240, 133, 0.8765, '文字识别']
        ]
    '''
    out_json = {"model_data": {"objects": [], "input_path": input_path}}
    
    # result 格式为 [bboxes, filename], 
    # 其中bboxes是一个list，每个item的格式为 [x1,y1,x2,y2,x3,y3,x4,y4,confidence]
    for bbox_dict in ocr_res["result"]:
        points = bbox_dict["box"]
        confidence = bbox_dict["box_score"]
        text = bbox_dict["text"] 
        text_score = bbox_dict["text_score"]  # 暂时没用到
        
        single_bbox = {
            "points":points,
            "conf": confidence,
            "name": text,
        }
        out_json['model_data']['objects'].append(single_bbox)


    return json.dumps(out_json)