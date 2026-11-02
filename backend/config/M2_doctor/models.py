from django.db import models

from M2_oldage_arrear.models import M2OldageArrearConsolidation


def _consolidation_fields():
    """
    Same columns as m2_oldage_arrear_consolidation. The consolidation save
    writes every one of them, so the doctor table must keep the same set.
    """
    return {
        field.name: field.clone()
        for field in M2OldageArrearConsolidation._meta.local_fields
        if not field.primary_key
    }


class _Meta:
    db_table = "m2_doctor_consolidation"
    verbose_name = "M2 doctor consolidation"
    ordering = ["-updated_at"]


M2DoctorConsolidation = type(
    "M2DoctorConsolidation",
    (models.Model,),
    {
        "__module__": __name__,
        "__doc__": "Doctor consolidation: last pay split into basic and NPA.",
        **_consolidation_fields(),
        # Last pay = last_basic + last_npa (salary earnings 001 + 005).
        "last_basic": models.DecimalField(
            max_digits=14, decimal_places=2, null=True, blank=True
        ),
        "last_npa": models.DecimalField(
            max_digits=14, decimal_places=2, null=True, blank=True
        ),
        "Meta": _Meta,
        "__str__": M2OldageArrearConsolidation.__str__,
        "tqs_display": M2OldageArrearConsolidation.tqs_display,
    },
)
