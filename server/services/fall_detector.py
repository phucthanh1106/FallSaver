import math
from collections import defaultdict, deque

class FallDetector:
    """Handles all fall detection logic"""
    
    def __init__(self, history_size=40, threshold_angle=36, threshold_drop=0.25):
        self.HISTORY = history_size
        self.THRESHOLD_ANGLE = threshold_angle
        self.THRESHOLD_DROP = threshold_drop
        
        self.info_history = defaultdict(lambda: {
            "angles": deque(maxlen=self.HISTORY),
            "xywh": deque(maxlen=self.HISTORY),
            "conf": deque(maxlen=self.HISTORY),
        })
    
    def body_angle(self, key_joints, conf):
        """Calculate body angle from keypoints"""
        # key_joints = [l_shoulder, r_shoulder, l_hip, r_hip, l_ankle, r_ankle]
        upper_avg_x = (key_joints[0][0] + key_joints[1][0]) / 2
        upper_avg_y = (key_joints[0][1] + key_joints[1][1]) / 2

        # Handle the case when the lower parts are all occluded
        if conf[2] < 0.1 and conf[3] < 0.1 and conf[4] < 0.1 and conf[5] < 0.1:
            return None
        
        # Ankles visible - use them
        if conf[4] > 0.2 and conf[5] > 0.2:
            lower_avg_x = (key_joints[4][0] + key_joints[5][0]) / 2
            lower_avg_y = (key_joints[4][1] + key_joints[5][1]) / 2
        # Hips visible - use them
        elif conf[2] > 0.2 and conf[3] > 0.2:
            lower_avg_x = (key_joints[2][0] + key_joints[3][0]) / 2
            lower_avg_y = (key_joints[2][1] + key_joints[3][1]) / 2
        else: 
            return None
        
        return math.degrees(math.atan2(abs(upper_avg_y - lower_avg_y), abs(upper_avg_x - lower_avg_x)))

    def fall_metrics(self, angles, xywh, fall_window):
        """Calculate fall metrics"""
        y_centers = [frame[1].item() for frame in xywh[-fall_window:]]
        max_y = max(y_centers)
        min_y = min(y_centers)
        initial_h = xywh[-fall_window:][0][3].item()
        initial_w = xywh[-fall_window:][0][2].item()
        last_h = xywh[-1][3].item()
        last_w = xywh[-1][2].item()

        angle_change = max(angles) - min(angles)

        # max_y should be when the person completely fell onto the floor/surface
        if y_centers.index(max_y) > y_centers.index(min_y):  
            # First standing position then laying  
            if initial_h / initial_w > 1:
                # Handle the normal laying position case
                if last_w > last_h: 
                    vertical_drop = (max_y - min_y) / initial_h
                # Handle the final position of person that results in a vertical bounding box
                else:
                    angle_change += 5
                    ave_h = (initial_h + last_h) / 2
                    vertical_drop = (max_y - min_y) / ave_h
            # First laying position then keep laying  
            else:
                # Handle the case when person switches from lying to standing
                if last_h / last_w > 1:
                    vertical_drop = 0
                # Handle the case when person falling in a horizontal posture
                else:
                    vertical_drop = (max_y - min_y) / initial_h - 0.05
                    angle_change = 90
        # This case means that the vertical change is upward not downward as in a fall
        else:
            vertical_drop = -(max_y - min_y) / initial_h

        return angle_change, vertical_drop

    def detect_fall(self, angles, xywh, conf, fall_window):
        # Reject if standing posture (high angle means upright)
        if angles[-1] > 60:
            return False
        
        # Use fall_metrics to calculate angle_change and vertical_drop
        angle_change, vertical_drop = self.fall_metrics(angles, xywh, fall_window)

        return angle_change >= self.THRESHOLD_ANGLE and vertical_drop >= self.THRESHOLD_DROP

    def update_history(self, person_id, angle, xywh, conf):
        """Update history for a person"""
        self.info_history[person_id]["angles"].append(angle)
        self.info_history[person_id]["xywh"].append(xywh)
        self.info_history[person_id]["conf"] = conf
    
    def get_history(self, person_id):
        """Get history for a person"""
        angles = list(self.info_history[person_id]["angles"])
        xywh = list(self.info_history[person_id]["xywh"])
        conf = float(self.info_history[person_id]["conf"])
        return angles, xywh, conf