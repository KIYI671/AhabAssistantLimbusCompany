from cv2 import imread, IMREAD_GRAYSCALE, createCLAHE


def get_grey_normalized_pic(pic_path):
    # 以灰度模式读取图像
    img = imread(pic_path, IMREAD_GRAYSCALE)

    # 自适应均衡化(均值化后更亮)
    clahe = createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    cl1 = clahe.apply(img)

    return cl1
