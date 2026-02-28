"""
Catégorisation de la pression artérielle selon les standards médicaux
Basé sur les guidelines AHA (American Heart Association)
"""

from typing import Tuple


class BloodPressureCategory:
    """Classe pour catégoriser la pression artérielle"""
    
    # Définitions des catégories selon le tableau standard
    NORMAL = "NORMAL"
    ELEVATED = "ELEVATED"
    STAGE1_HYPERTENSION = "STAGE1_HYPERTENSION"
    STAGE2_HYPERTENSION = "STAGE2_HYPERTENSION"
    HYPERTENSIVE_CRISIS = "HYPERTENSIVE_CRISIS"
    
    @staticmethod
    def categorize(systolic: int, diastolic: int) -> Tuple[str, str]:
        """
        Catégorise la pression artérielle selon les standards médicaux
        
        Args:
            systolic: Pression systolique (mmHg)
            diastolic: Pression diastolique (mmHg)
            
        Returns:
            Tuple (category, description)
        """
        # HYPERTENSIVE CRISIS (consult your doctor immediately)
        # Higher than 180 (Systolic) AND/OR Higher than 120 (Diastolic)
        if systolic > 180 or diastolic > 120:
            return (
                BloodPressureCategory.HYPERTENSIVE_CRISIS,
                "HYPERTENSIVE CRISIS (consult your doctor immediately)"
            )
        
        # HIGH BLOOD PRESSURE (HYPERTENSION) STAGE 2
        # 140 or higher (Systolic) OR 90 or higher (Diastolic)
        if systolic >= 140 or diastolic >= 90:
            return (
                BloodPressureCategory.STAGE2_HYPERTENSION,
                "HIGH BLOOD PRESSURE (HYPERTENSION) STAGE 2"
            )
        
        # HIGH BLOOD PRESSURE (HYPERTENSION) STAGE 1
        # 130-139 (Systolic) OR 80-89 (Diastolic)
        if (130 <= systolic <= 139) or (80 <= diastolic <= 89):
            return (
                BloodPressureCategory.STAGE1_HYPERTENSION,
                "HIGH BLOOD PRESSURE (HYPERTENSION) STAGE 1"
            )
        
        # ELEVATED
        # 120-129 (Systolic) AND Less than 80 (Diastolic)
        if 120 <= systolic <= 129 and diastolic < 80:
            return (
                BloodPressureCategory.ELEVATED,
                "ELEVATED"
            )
        
        # NORMAL
        # Less than 120 (Systolic) AND Less than 80 (Diastolic)
        return (
            BloodPressureCategory.NORMAL,
            "NORMAL"
        )
    
    @staticmethod
    def get_category_color(category: str) -> str:
        """Retourne la couleur associée à la catégorie"""
        colors = {
            BloodPressureCategory.NORMAL: "#4CAF50",  # Vert
            BloodPressureCategory.ELEVATED: "#FFC107",  # Jaune
            BloodPressureCategory.STAGE1_HYPERTENSION: "#FF9800",  # Orange
            BloodPressureCategory.STAGE2_HYPERTENSION: "#F44336",  # Rouge
            BloodPressureCategory.HYPERTENSIVE_CRISIS: "#8B0000"  # Rouge foncé
        }
        return colors.get(category, "#757575")  # Gris par défaut
    
    @staticmethod
    def get_category_info() -> dict:
        """Retourne les informations sur toutes les catégories"""
        return {
            BloodPressureCategory.NORMAL: {
                "systolic_range": "< 120",
                "diastolic_range": "< 80",
                "color": "#4CAF50",
                "description": "NORMAL"
            },
            BloodPressureCategory.ELEVATED: {
                "systolic_range": "120-129",
                "diastolic_range": "< 80",
                "color": "#FFC107",
                "description": "ELEVATED"
            },
            BloodPressureCategory.STAGE1_HYPERTENSION: {
                "systolic_range": "130-139",
                "diastolic_range": "80-89",
                "color": "#FF9800",
                "description": "HIGH BLOOD PRESSURE (HYPERTENSION) STAGE 1"
            },
            BloodPressureCategory.STAGE2_HYPERTENSION: {
                "systolic_range": "≥ 140",
                "diastolic_range": "≥ 90",
                "color": "#F44336",
                "description": "HIGH BLOOD PRESSURE (HYPERTENSION) STAGE 2"
            },
            BloodPressureCategory.HYPERTENSIVE_CRISIS: {
                "systolic_range": "> 180",
                "diastolic_range": "> 120",
                "color": "#8B0000",
                "description": "HYPERTENSIVE CRISIS (consult your doctor immediately)"
            }
        }
