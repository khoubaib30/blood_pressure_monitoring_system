"""
Patient Profile for realistic blood pressure data generation
Each patient maintains consistent baseline and trends over time
"""

import random
import math
from datetime import datetime, timedelta
from typing import Tuple


class PatientProfile:
    """Represents a patient with consistent baseline and trends"""
    
    def __init__(self, patient_id: str, device_id: str):
        """
        Initialize a patient profile with baseline values
        
        Args:
            patient_id: Unique patient identifier
            device_id: Device identifier for this patient
        """
        self.patient_id = patient_id
        self.device_id = device_id
        
        # Initialize baseline BP (realistic medical ranges)
        # Random baseline within normal to hypertensive ranges
        baseline_systolic = random.randint(95, 160)
        baseline_diastolic = random.randint(60, 100)
        
        # Ensure realistic ratio (systolic/diastolic ~1.5-2.0)
        if baseline_diastolic > 0:
            ratio = baseline_systolic / baseline_diastolic
            if ratio < 1.4:
                baseline_diastolic = int(baseline_systolic / 1.6)
            elif ratio > 2.2:
                baseline_diastolic = int(baseline_systolic / 1.8)
        
        self.baseline_systolic = baseline_systolic
        self.baseline_diastolic = baseline_diastolic
        
        # Initialize trend (improving, worsening, or stable)
        # Trend represents change per day in mmHg
        trend_type = random.choice(['improving', 'worsening', 'stable'])
        if trend_type == 'improving':
            self.trend_systolic = random.uniform(-1.5, -0.3)  # Decreasing
            self.trend_diastolic = random.uniform(-1.0, -0.2)
        elif trend_type == 'worsening':
            self.trend_systolic = random.uniform(0.3, 1.5)  # Increasing
            self.trend_diastolic = random.uniform(0.2, 1.0)
        else:  # stable
            self.trend_systolic = random.uniform(-0.2, 0.2)  # Minimal change
            self.trend_diastolic = random.uniform(-0.15, 0.15)
        
        # Baseline heart rate (correlated with BP)
        if baseline_systolic < 120:
            self.baseline_heart_rate = random.randint(60, 75)
        elif baseline_systolic < 140:
            self.baseline_heart_rate = random.randint(70, 85)
        else:
            self.baseline_heart_rate = random.randint(75, 95)
        
        # Track state
        self.observation_count = 0
        self.start_time = datetime.now()
        self.last_observation_time = None
        
        # Event state (for stress/medication events)
        self.active_stress_event = False
        self.stress_event_remaining = 0
        self.medication_effect_active = False
        self.medication_effect_remaining = 0
        self.medication_effect_magnitude = 0
    
    def get_current_bp(self, current_time: datetime) -> Tuple[int, int, int]:
        """
        Calculate current blood pressure based on baseline, trend, and patterns
        
        Args:
            current_time: Current timestamp
            
        Returns:
            Tuple (systolic, diastolic, heart_rate)
        """
        # Calculate time since start (for trend)
        # Use hours instead of days for more responsive trends
        if self.last_observation_time:
            time_delta = current_time - self.start_time
            hours_elapsed = time_delta.total_seconds() / 3600  # seconds to hours
            days_elapsed = hours_elapsed / 24  # Convert to days for trend calculation
        else:
            days_elapsed = 0
            hours_elapsed = 0
        
        # Apply trend
        current_systolic = self.baseline_systolic + (self.trend_systolic * days_elapsed)
        current_diastolic = self.baseline_diastolic + (self.trend_diastolic * days_elapsed)
        
        # Daily cycle (circadian rhythm)
        hour = current_time.hour
        # Morning (6-10): +5-10 mmHg, Afternoon: baseline, Evening: -3-7, Night: -5-10
        if 6 <= hour < 10:
            cycle_factor = random.uniform(5, 10)
        elif 10 <= hour < 18:
            cycle_factor = random.uniform(-2, 2)
        elif 18 <= hour < 22:
            cycle_factor = random.uniform(-7, -3)
        else:  # 22-6 (night)
            cycle_factor = random.uniform(-10, -5)
        
        current_systolic += cycle_factor
        current_diastolic += cycle_factor * 0.7  # Diastolic follows but less
        
        # Random noise (Gaussian-like, ±4-6 mmHg)
        noise_systolic = random.gauss(0, 4.5)
        noise_diastolic = random.gauss(0, 3.5)
        
        current_systolic += noise_systolic
        current_diastolic += noise_diastolic
        
        # Handle stress events
        if self.active_stress_event:
            current_systolic += random.uniform(15, 25)
            current_diastolic += random.uniform(10, 18)
            self.stress_event_remaining -= 1
            if self.stress_event_remaining <= 0:
                self.active_stress_event = False
        else:
            # Random chance of stress event
            # Higher probability for patients with high baseline BP
            stress_probability = 0.075  # Default 7.5%
            if self.baseline_systolic > 150:
                stress_probability = 0.15  # 15% for high-risk patients
            elif self.baseline_systolic > 140:
                stress_probability = 0.10  # 10% for medium-risk patients
            
            if random.random() < stress_probability:
                self.active_stress_event = True
                # Longer stress events for high-risk patients
                if self.baseline_systolic > 150:
                    self.stress_event_remaining = random.randint(3, 6)
                else:
                    self.stress_event_remaining = random.randint(2, 4)
        
        # Handle medication effects
        if self.medication_effect_active:
            current_systolic += self.medication_effect_magnitude
            current_diastolic += self.medication_effect_magnitude * 0.7
            self.medication_effect_remaining -= 1
            if self.medication_effect_remaining <= 0:
                self.medication_effect_active = False
        else:
            # Random chance of medication effect (3-5% per observation)
            if random.random() < 0.04:
                self.medication_effect_active = True
                self.medication_effect_remaining = random.randint(3, 6)
                self.medication_effect_magnitude = random.uniform(-15, -5)  # Negative (decrease)
        
        # Ensure diastolic follows systolic (correlation ~0.75)
        # If systolic changed significantly, diastolic should follow
        systolic_change = current_systolic - self.baseline_systolic
        diastolic_adjustment = systolic_change * 0.6  # Correlation factor
        current_diastolic += diastolic_adjustment
        
        # Calculate heart rate (correlated with BP)
        bp_elevation = (current_systolic - self.baseline_systolic) / 10
        heart_rate = self.baseline_heart_rate + int(bp_elevation * 2)
        
        # Add some variation to heart rate
        heart_rate += random.randint(-5, 5)
        
        # Ensure realistic bounds
        current_systolic = max(80, min(220, int(current_systolic)))
        current_diastolic = max(50, min(140, int(current_diastolic)))
        heart_rate = max(50, min(120, heart_rate))
        
        # Update state
        self.observation_count += 1
        self.last_observation_time = current_time
        
        return int(current_systolic), int(current_diastolic), heart_rate
