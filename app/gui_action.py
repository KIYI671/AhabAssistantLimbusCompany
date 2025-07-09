from app import task_check_box


def select_all():
    for check_box in task_check_box[:5]:
        check_box.setChecked(True)

def clear_all():
    for check_box in task_check_box[:5]:
        check_box.setChecked(False)

def link_start():
    print("link start")