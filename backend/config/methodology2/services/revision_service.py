from methodology2.services.lookup_service import (get_scale_by_code)
from methodology2.services.scale_parser import (get_next_higher_stage)

def revise_pay(
    scale_code,
    from_column,
    to_column,
    current_pay,
    fitment_factor=1
):

    scale_data = get_scale_by_code(scale_code)

    old_scale = scale_data[from_column]

    new_scale = scale_data[to_column]

    revised_amount = current_pay * fitment_factor

    fixed_pay = get_next_higher_stage(
        new_scale,
        revised_amount
    )

    return {
        'old_scale': old_scale,
        'new_scale': new_scale,
        'current_pay': current_pay,
        'revised_amount': revised_amount,
        'fixed_pay': fixed_pay
    }