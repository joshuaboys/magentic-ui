# This Script is slightly modified from the creators of the AssistantBench dataset https://huggingface.co/spaces/AssistantBench/leaderboard/blob/main/evaluation/evaluator.py
import json
from .evaluate_factory import get_evaluator
import numpy as np


def find_isnan(samp):
    try:
        if np.isnan(samp):
            return True
        else:
            return False
    except (TypeError, ValueError):
        return False


def fix_ans(answer):
    try:
        answer = (
            answer.replace("{'", '{"')
            .replace("', '", '", "')
            .replace("': '", '": "')
            .replace("'}", '"}')
        )
        answer = answer.replace("': ", '": ')
        return answer
    except (AttributeError, TypeError):
        return answer


def parse_answer(answer):
    if len(answer) == 1:
        ans, is_num = fix_number(answer[0])
        if is_num:
            return ans, "number"
        try:
            ans = json.loads(fix_ans(answer[0]))
            return [ans], "json"
        except json.JSONDecodeError:
            ans, is_num = fix_number(answer[0])
            if is_num:
                return ans, "number"
            else:
                return answer[0], "string"
    else:
        try:
            ans = [json.loads(fix_ans(ex)) for ex in answer]
            return ans, "json"
        except json.JSONDecodeError:
            return answer, "string list"


def fix_number(number):
    if isinstance(number, str):
        copy_ans = number
        copy_ans = " ".join(
            " ".join(" ".join(copy_ans.split("$")).split("%")).split("sqft")
        ).strip()
        copy_ans = copy_ans.strip()
        copy_ans = copy_ans.replace(",", ".").replace(" square kilometers", "")
        try:
            return float(copy_ans), True
        except ValueError:
            return number, False
    elif isinstance(number, int):
        return float(number), True
    else:
        return number, True


def fix_prediction(prediction, gold_answer, evaluator):
    if (
        isinstance(prediction, list)
        and len(prediction) == 1
        and (
            isinstance(prediction[0], int)
            or (isinstance(prediction[0], str) and prediction[0].isnumeric())
        )
    ):
        prediction = fix_number(prediction[0])

    if not isinstance(prediction, list):
        prediction, is_num = fix_number(prediction)
        if evaluator == "json":
            try:
                prediction = [json.loads(pred) for pred in prediction.split("\n")]  # type: ignore
            except json.JSONDecodeError:
                prediction = [prediction]

    if (hasattr(type(prediction), "__len__")) and (len(prediction) == 0):  # type: ignore
        return prediction, False

    if (isinstance(prediction, list) and len(prediction) > 1) and isinstance(
        gold_answer, float
    ):
        return prediction, False

    return prediction, True


def ab_question_scorer(prediction, gold_answer):
    """
    prediction: str or list of str
    gold_answer: str or list of str

    returns a float between 0 and 1
    """
    try:
        try:
            prediction = json.loads(prediction)
        except json.JSONDecodeError:
            prediction = prediction

        answer_list = (
            [x for x in gold_answer.split("\n") if len(x.strip()) > 0]
            if not isinstance(gold_answer, list)
            else gold_answer
        )
        gold_answer, evaluator = parse_answer(answer_list)
        prediction, run_eval = fix_prediction(prediction, gold_answer, evaluator)

        # if (not isinstance(prediction, float) and len(prediction) == 0) or find_isnan(
        #     prediction
        # ):
        #     has_ans = 0.0

        if not run_eval:
            return 0.0

        metric_eval = get_evaluator(evaluator)
        accuracy = metric_eval(prediction, gold_answer)
        # double check if the accuracy is a number between 0 and 1
        if 0 <= accuracy <= 1:
            return accuracy
        else:
            # throw exception
            raise ValueError(
                f"Accuracy should be a float between 0 and 1, but got {accuracy}"
            )
    except Exception as e:
        print(
            f"Something went wrong while evaluating prediction {prediction} vs gold answer {gold_answer} with error {e}"
        )
        return 0.0
