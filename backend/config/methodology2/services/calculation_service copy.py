from datetime import datetime

from methodology2.services.sda_service import (get_special_da, get_special_da_1980, get_fixed_da_1988)
from methodology2.services.scale_parser import ( fix_pay_in_scale,    get_next_nth_stage, align_pay_with_increment, align_pay_without_increment)
from methodology2.services.scale_service import (get_next_revision)
from methodology2.services.matrix_service import (fix_pay_in_matrix_2017, fix_pay_in_matrix_2022)

def calculate_1979_to_1984(scales, current_revision, last_pay):
    basic_pay = float(last_pay)
    fixed_da = 150
    special_da = get_special_da_1980(
        basic_pay
    )
    notional_pay = (
        basic_pay +
        fixed_da +
        special_da
    )
    print("current_revision=", current_revision)

    next_revision = get_next_revision(
        current_revision
        )

    target_scale = scales[
            next_revision
        ]

    pay_after_two_increments = (
            align_pay_with_increment(
                notional_pay,
                target_scale,
                2
            )
        )
    vda_1984=237.85
    if pay_after_two_increments <= 619:
        fda_1984=212.40
    elif pay_after_two_increments >= 620 and pay_after_two_increments <= 769:    
        fda_1984=217.40
    elif pay_after_two_increments >= 770 and pay_after_two_increments <= 869:
        fda_1984=222.40
    else:
        fda_1984=227.40

    pre_notional_pay=(pay_after_two_increments+vda_1984+fda_1984)
    fitment=get_special_da( pre_notional_pay  )

    notional_pay_1984=pre_notional_pay + fitment

    next_revision_2 = get_next_revision(
    next_revision
        )
    target_scale_2 = scales[
        next_revision_2
    ]
    pay_after_one_increments = (
        align_pay_with_increment(
            notional_pay_1984,
            target_scale_2,
            1
        )
    )
    vda_1988=778.45
    special_da_1988 = get_special_da(pay_after_two_increments)
    fixed_da_1988 = get_fixed_da_1988(pay_after_one_increments)
    fitment_1988 = round(pay_after_one_increments*12.5/100,2)
    notional_pay_1988 = round(pay_after_one_increments + vda_1988 + special_da_1988 + fixed_da_1988 + fitment_1988,2)

    next_revision_3 = get_next_revision(
        next_revision_2
    )

    target_scale_3 = scales[
        next_revision_3
    ]

    basic_pay_1994 = align_pay_without_increment(
        notional_pay_1988,
        target_scale_3
    )
    if basic_pay_1994 <= 3000:
        special_allowance=round(basic_pay_1994*0.02, 0)
    else:
        special_allowance=round(basic_pay_1994*0.04, 0)

    if basic_pay_1994 <= 3500:
        vda_1994=round(basic_pay_1994*0.554, 2)
        if vda_1994<1218:
            vda_1994=1218
        else:
            vda_1994=vda_1994
    elif basic_pay_1994 >= 3501 and basic_pay_1994 <= 6500:
        vda_1994=round(basic_pay_1994*0.415, 2)
        if vda_1994<1939:
            vda_1994=1939
        else:
            vda_1994=vda_1994
    elif basic_pay_1994 >= 6501 and basic_pay_1994 <= 9500:
        vda_1994=round(basic_pay_1994*0.332, 2)
        if vda_1994<2701:
            vda_1994=2701
        else:
            vda_1994=vda_1994
    else:
        vda_1994=round(basic_pay_1994*0.277, 2)
        if vda_1994<3158:
            vda_1994=3158
        else:
            vda_1994=vda_1994
    cpi_difference_1994=138
    fitment_1994=round(basic_pay_1994*0.275, 2 )
    notional_pay_1994=round(basic_pay_1994 + special_allowance + vda_1994 + cpi_difference_1994 + fitment_1994, 2)


    next_revision_4 = get_next_revision(
        next_revision_3
    )

    target_scale_4 = scales[
        next_revision_4
    ]

    basic_pay_1997 = align_pay_with_increment(
        notional_pay_1994,
        target_scale_4,1
    )
    da_1997=round(basic_pay_1997*0.782, 2)
    fitment_1997=round((basic_pay_1997 + da_1997)*0.23, 2)
    notional_pay_1997=(basic_pay_1997 + da_1997 + fitment_1997)
    final_1997= ((int(notional_pay_1997) + 9) // 10) * 10 

    basic_pay_2007=final_1997
    variable_da_2007=round(basic_pay_2007*0.5714, 2)
    fitment_2007=round((basic_pay_2007 + variable_da_2007)*0.105, 2)
    notional_pay_2007=round(basic_pay_2007 + variable_da_2007 + fitment_2007, 2)

    basic_pay_2012=((int(notional_pay_2007) + 9) // 10) * 10
    variable_da_2012=round(basic_pay_2012*0.40, 2)
    fitment_2012=round((basic_pay_2012 + variable_da_2012)*0.106, 2)
    notional_pay_2012=round(basic_pay_2012 + variable_da_2012 + fitment_2012, 2)    

    basic_pay_2017=((int(notional_pay_2012) + 9) // 10) * 10

    next_revision_5 = get_next_revision(
        next_revision_4
    )
    target_scale_5 = scales[
        next_revision_5
    ]
    next_revision_6 = get_next_revision(
        next_revision_5
    )
    target_scale_6 = scales[
        next_revision_6
    ]
    next_revision_7 = get_next_revision(
        next_revision_6
    )
    target_scale_7 = scales[
        next_revision_7
    ]

    
    matrix_pay_2017 = fix_pay_in_matrix_2017(
    target_scale_6,
    basic_pay_2017
    )
    da_2017=round(matrix_pay_2017*0.30, 2)
    fitment_2017=round((matrix_pay_2017)*0.085, 2)
    notional_pay_2017=round(matrix_pay_2017 + da_2017 + fitment_2017, 2)

    basic_pay_2022=fix_pay_in_matrix_2022(target_scale_7, notional_pay_2017)
    print("Basic_2022=", basic_pay_2022)

    return [

        {
            "row": 27,
            "description": "Basic Pay",
            "value": basic_pay
        },

        {
            "row": 28,
            "description": "Fixed DA",
            "value": fixed_da
        },

        {
            "row": 29,
            "description": "Special Allowance",
            "value": special_da
        },

        {
            "row": 30,
            "description": "Notional Pay",
            "value": round(
                notional_pay,
                2
            )
        },
        {
            "row": 31,
            "description": "Basic Pay after 2 increments (1984 scale)",
            "value": pay_after_two_increments
        },
        {
            "row": 32,
            "description": "VDA from 455 to 607(1984)",
            "value": vda_1984
        },
        {
            "row": 33,
            "description": "FDA (1984)",
            "value": fda_1984
        },
        
        {
            "row": 34,
            "description": "Fitment",
            "value": fitment
        },
        {
            "row": 35,
            "description": "Notional Pay (1984)",
            "value": notional_pay_1984
        },
        {
            "row": 36,
            "description": "Basic Pay (1988 scale after 1 increment)",
            "value": pay_after_one_increments
        },
        {
            "row": 37,
            "description": "VDA (1988)",
            "value": vda_1988
        },
        {
            "row": 38,
            "description": "Special Allowance (1988)",
            "value": special_da_1988
        },
        {
            "row": 39,
            "description": "Fixed DA (1988)",
            "value": fixed_da_1988
        },
        {
            "row": 40,
            "description": "Fitment (1988)",
            "value": fitment_1988
        },
        {
            "row": 41,
            "description": "Notional Pay (1988)",
            "value": notional_pay_1988
        },
        {
            "row": 42,
            "description": "Basic Pay (1994 scale)",
            "value": basic_pay_1994
        },
        {
            "row": 43,
            "description": "Special Allowance (1994)",
            "value": special_allowance
        },
        {
            "row": 44,
            "description": "VDA (1994)",
            "value": vda_1994
        },
        {
            "row": 45,
            "description": "CPI Difference (1994)",
            "value": cpi_difference_1994
        },
        {
            "row": 46,
            "description": "Fitment (1994)",
            "value": fitment_1994
        },
        {
            "row": 47,
            "description": "Notional Pay (1994)",
            "value": notional_pay_1994
        },
        {
            "row": 48,
            "description": "Basic Pay (1997 scale after 1 increment)",
            "value": basic_pay_1997
        },
        {
            "row": 49,
            "description": "DA (1997)",
            "value": da_1997
        },
        {
            "row": 50,
            "description": "Fitment (1997)",
            "value": fitment_1997
        },
        {
            "row": 51,
            "description": "Notional Pay (1997)",
            "value": final_1997
        },
        {
            "row": 52,
            "description": "Basic Pay (2007 scale)",
            "value": basic_pay_2007
        },
        {
            "row": 53,
            "description": "Variable DA (2007)",
            "value": variable_da_2007
        },
        {
            "row": 54,
            "description": "Fitment (2007)",
            "value": fitment_2007
        },
        {
            "row": 55,
            "description": "Notional Pay (2007)",
            "value": notional_pay_2007
        },
        {
            "row": 56,
            "description": "Basic Pay (2012 scale)",
            "value": basic_pay_2012
        },
        {
            "row": 57,
            "description": "Variable DA (2012)",
            "value": variable_da_2012
        },
        {
            "row": 58,
            "description": "Fitment (2012)",
            "value": fitment_2012
        },
        {
            "row": 59,
            "description": "Notional Pay (2012)",
            "value": notional_pay_2012
        },
        {
            "row": 60,
            "description": "Basic Pay (2017 scale)",
            "value": basic_pay_2017
        },
        {
            "row": 61,
            "description": "Pay after fixing in Matrix (2017)",
            "value": matrix_pay_2017
         },
        {
            "row": 62,
            "description": "DA (2017)",
            "value": da_2017
        },
        {
            "row": 63,
            "description": "Fitment (2017)",
            "value": fitment_2017
        },
        {
            "row": 64,
            "description": "Notional Pay (2017)",
            "value": notional_pay_2017
        },
        {
            "row": 65,
            "description": "Basic Pay (2022 scale)",
            "value": basic_pay_2022
        }


    ]