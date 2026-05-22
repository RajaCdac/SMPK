REVISIONS_WITH_INCREMENT_10 = (
    "2007(126 CPI)",
    "2012(198 CPI)",
)


def expand_scale_increment_10(scale_string):
    """
    2007 / 2012 scales use min-10-max. Oracle may return min-max only
    (e.g. 21000-53500 → 21000-10-53500).
    """
    if not scale_string:
        return scale_string

    cleaned = str(scale_string).strip()
    parts = [p.strip() for p in cleaned.split("-") if p.strip()]
    numbers = []
    for part in parts:
        try:
            numbers.append(int(part))
        except ValueError:
            return cleaned

    if len(numbers) == 2:
        return f"{numbers[0]}-10-{numbers[1]}"
    return cleaned


def normalize_scale_for_revision(scale_string, revision_column=None):
    if revision_column in REVISIONS_WITH_INCREMENT_10:
        return expand_scale_increment_10(scale_string)
    return scale_string


#Converts pay scale text into structured segments.
def parse_scale(scale_string):
    if not scale_string:
        return []
    parts = scale_string.split('-')
    numbers = [int(x) for x in parts]
    if len(numbers) == 2:
        return [{
            "start": numbers[0],
            "increment": 10,
            "end": numbers[1],
        }]
    if len(numbers) < 3:
        return []
    else:
        parsed = []
        current_start = numbers[0]
        i = 1
        while i < len(numbers):
            increment = numbers[i]
            end = numbers[i + 1]
            parsed.append({
                'start': current_start,
                'increment': increment,
                'end': end
            })
            current_start = end
            i += 2
        return parsed
    
#Generates every valid pay stage in a scale.
def generate_pay_stages(scale_string):
    parsed_scale = parse_scale(scale_string)
    if not parsed_scale:
        return []   
    else:
        stages = []
        for segment in parsed_scale:
            current = segment['start']
            while current <= segment['end']:
                if current not in stages:
                    stages.append(current)
                current += segment['increment']
        return stages
    
#Finds equal or next higher pay stage.
def get_next_higher_stage(scale_string, amount):
    stages = generate_pay_stages(scale_string)
    if not stages:
        return None
    else:
        for stage in stages:
            if stage >= amount:
                return stage
        return stages[-1]

#Gives future increment stage.
def get_next_nth_stage(scale_string, current_pay, increment_count):
    stages = generate_pay_stages(scale_string)
    if current_pay not in stages:
        return None
    current_index = stages.index(current_pay)    
    next_index = (current_index + increment_count)
    if next_index >= len(stages):
        next_index = len(stages) - 1
    return stages[next_index]

#Pay Fixation.
def fix_pay_in_scale(scale_string, amount):
    return get_next_higher_stage(scale_string, amount)

#Pay Fixation with increment.
def align_pay_with_increment(amount, target_scale, increment_count):
    fixed_pay = fix_pay_in_scale( target_scale, int(amount))
    revised_pay = get_next_nth_stage( target_scale, fixed_pay, increment_count)
    return revised_pay

#Pay Fixation with increment.
def align_pay_without_increment(amount, target_scale):
    fixed_pay = fix_pay_in_scale( target_scale, int(amount))
    return fixed_pay