import math
from collections import defaultdict, deque

class FallDetector:
    """Handles all fall detection logic"""
    
    def __init__(self, history_size=40, threshold_angle=40, threshold_drop=0.28):
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

        # Handle the case when the lower parts are occluded
        if (conf[2] < 0.05 and conf[3] < 0.05) and (conf[4] < 0.05 and conf[5] < 0.05):
            return None
        
        # Ankles visible - use them
        if conf[4] > 0.2 or conf[5] > 0.2:
            lower_avg_x = (key_joints[4][0] + key_joints[5][0]) / 2
            lower_avg_y = (key_joints[4][1] + key_joints[5][1]) / 2
        # Hips visible - use them
        elif conf[2] > 0.2 or conf[3] > 0.2:
            lower_avg_x = (key_joints[2][0] + key_joints[3][0]) / 2
            lower_avg_y = (key_joints[2][1] + key_joints[3][1]) / 2
        else: 
            return None
            # lower_avg_x = (key_joints[4][0] + key_joints[5][0]) / 2
            # lower_avg_y = (key_joints[4][1] + key_joints[5][1]) / 2
        
        return math.degrees(math.atan2(abs(upper_avg_y - lower_avg_y), abs(upper_avg_x - lower_avg_x)))

    def fall_metrics(self, angles, xywh, fall_window):
        """Calculate fall metrics"""
        # Track the top of the box instead of its center. The top follows the
        # person's upper body and moves farther downward during a fall.
        average_positions = [( (frame[1].item() - frame[3].item() / 2) + frame[1].item() ) / 2 for frame in xywh[-fall_window:]]
                
        max_y = max(average_positions)
        min_y = min(average_positions)
        index_min_y = average_positions.index(min_y)
        index_max_y = average_positions.index(max_y)

        initial_h = xywh[-fall_window:][index_min_y][3].item()
        initial_w = xywh[-fall_window:][index_min_y][2].item()
        last_h = xywh[-len(average_positions) + index_max_y][3].item()
        last_w = xywh[-len(average_positions) + index_max_y][2].item()
        ave_h = (initial_h + last_h) / 2

        # For debugging case
        case = 0

        angle_change = max(angles) - min(angles)

        # max_y should be when the person's upper body is closest to the floor.
        POSTURE_RATIO = 1.15
        initial_ratio = initial_h / initial_w
        last_ratio = last_h / last_w
        initial_is_vertical = initial_ratio > POSTURE_RATIO
        last_is_vertical = last_ratio > POSTURE_RATIO

        if index_max_y > index_min_y and max_y / min_y > 1.15:
            # First standing position then laying  
            if initial_is_vertical:
                vertical_drop = (max_y - min_y) / ave_h
                # Handling edge cases
                if vertical_drop > 2:
                    vertical_drop = 0
                # Handle the normal laying position case
                if not last_is_vertical: 
                    case = 1
                # Handle the final position of person that results in a vertical bounding box
                else:
                    case = 2
            # First laying position then keep laying  
            else:
                # Handle the case when person switches from lying to standing
                if last_is_vertical:
                    case = 3
                    vertical_drop = 0
                # Handle the case when person falling in a horizontal posture
                else:
                    case = 4
                    vertical_drop = (max_y - min_y) / ave_h
                    angle_change = 90
        # This case means that the vertical change is upward not downward as in a fall
        else:
            vertical_drop = -(max_y - min_y) / initial_h

        return angle_change, vertical_drop, case

    def detect_fall(self, angles, xywh, conf, fall_window):
        # Reject if standing posture (high angle means upright)
        if angles[-1] > 60:
            return False
        
        # Use fall_metrics to calculate angle_change and vertical_drop
        angle_change, vertical_drop, _ = self.fall_metrics(angles, xywh, fall_window)

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
