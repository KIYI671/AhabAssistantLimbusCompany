import cv2
import numpy as np


# TODO: 合并入image_utils
# 先能跑就行

def cal_ccoeff_confidence(im_source, im_search):
    res_temp = cv2.matchTemplate(im_source, im_search, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res_temp)
    return max_val

def cal_confidence(im_source, im_search):
    """
    将截图和识别结果缩放到大小一致,并计算可信度
    Args:
        im_source: 待匹配图像
        im_search: 图片模板
        rgb:是否使用rgb通道进行校验

    Returns: confidence:可信度

    """
    h, w = im_source.shape
    im_search = cv2.resize(im_search, (w,h), interpolation=cv2.INTER_AREA)
    confidence = cal_ccoeff_confidence(im_source=im_source, im_search=im_search)
    confidence = (1 + confidence) / 2
    return confidence

def get_perspective_area_rect(im_source, src):
    """
    根据矩形四个顶点坐标,获取在原图中的最大外接矩形

    Args:
        im_source: 待匹配图像
        src: 目标图像中相应四边形顶点的坐标

    Returns:
        最大外接矩形
    """
    h, w = im_source.shape

    x = [int(i[0]) for i in src]
    y = [int(i[1]) for i in src]
    # 计算边界并约束在图像范围内 (利用嵌套max/min一步完成边界约束)
    x_min = max(min(x), 0)
    x_max = min(max(x), w - 1)
    y_min = max(min(y), 0)
    y_max = min(max(y), h - 1)
    return x_min, y_min, x_max - x_min, y_max - y_min

def find_homography(sch_pts, src_pts):
    """
    多组特征点对时，求取单向性矩阵
    """
    try:
        M, mask = cv2.findHomography(sch_pts, src_pts, cv2.USAC_MAGSAC, 4.0, None, 2000, 0.99)
    except cv2.error:
        import traceback
        traceback.print_exc()
    else:
        if mask is not None:
            return M, mask

def _perspective_transform(im_source, im_search, src, dst):
    """
    根据四对对应点计算透视变换, 并裁剪相应图片

    Args:
        im_source: 待匹配图像
        im_search: 待匹配模板
        src: 目标图像中相应四边形顶点的坐标 (左上,右上,左下,右下)
        dst: 源图像中四边形顶点的坐标 (左上,右上,左下,右下)

    Returns:

    """
    h, w = im_search.shape
    matrix = cv2.getPerspectiveTransform(src=src, dst=dst)
    output = cv2.warpPerspective(im_source, matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT,
                               borderValue=0)

    return output

def handle_many_good_points(im_source, im_search, kp_src, kp_sch, good):
    """
    特征点匹配数量>=4时,使用单矩阵映射,获取识别的目标图片

    Args:
        im_source: 待匹配图像
        im_search: 图片模板
        kp_sch: 关键点集
        kp_src: 关键点集
        good: 描述符集

    Returns:
        透视变换后的图片
    """
    sch_pts, img_pts = np.float32([kp_sch[m.queryIdx].pt for m in good]).reshape(
        -1, 1, 2), np.float32([kp_src[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
    # M是转化矩阵
    M, mask = find_homography(sch_pts, img_pts)
    # 计算四个角矩阵变换后的坐标，也就是在大图中的目标区域的顶点坐标:
    a,b = im_search.shape
    h, w = im_search.shape
    h_s, w_s = im_source.shape
    pts = np.float32([[0, 0], [0, h - 1], [w - 1, h - 1], [w - 1, 0]]).reshape(-1, 1, 2)
    try:
        dst: np.ndarray = cv2.perspectiveTransform(pts, M)
        pypts = [tuple(npt[0]) for npt in dst.tolist()]
        src = np.array([pypts[0], pypts[3], pypts[1], pypts[2]], dtype=np.float32)
        dst = np.float32([[0, 0], [w, 0], [0, h], [w, h]])
        output = _perspective_transform(im_source=im_source, im_search=im_search, src=src, dst=dst)

    except cv2.error as err:
        raise err

    rect = get_perspective_area_rect(im_source=im_source, src=src)

    return output, rect

def extract_good_points(im_source, im_search, kp_src, kp_sch, good, angle, rgb):
    """
    根据匹配点(good)数量,提取识别区域

    Args:
        im_source: 待匹配图像
        im_search: 图片模板
        kp_src: 关键点集
        kp_sch: 关键点集
        good: 描述符集
        angle: 旋转角度
        rgb: 是否使用rgb通道进行校验

    Returns:
        范围,和置信度
    """
    len_good = len(good)
    confidence, rect, target_img = None, None, None

    if len_good > 4 :
        target_img, rect = handle_many_good_points(im_source=im_source, im_search=im_search,
                                                   kp_sch=kp_sch, kp_src=kp_src, good=good)
    else:
        target_img =None

    if target_img is not None:
        confidence = cal_confidence(im_source=im_search, im_search=target_img)


    return rect, confidence

def filter_good_point(matches, kp_src, kp_sch, kp_sch_point, kp_src_matches_point):
    """ 筛选最佳点 """
    # 假设第一个点,及distance最小的点,为基准点
    sort_list = [sorted(match, key=lambda x: x is np.nan and float('inf') or x.distance)[0]
                 for match in matches]
    sort_list = [v for v in sort_list if v is not np.nan]

    first_good_point: cv2.DMatch = sorted(sort_list, key=lambda x: x.distance)[0]
    first_good_point_train: cv2.KeyPoint = kp_src[first_good_point.trainIdx]
    first_good_point_query: cv2.KeyPoint = kp_sch[first_good_point.queryIdx]
    first_good_point_angle = first_good_point_train.angle - first_good_point_query.angle

    def get_points_origin_angle(point_x, point_y, offset):
        points_origin_angle = np.arctan2(
            (point_y - offset.pt[1]),
            (point_x - offset.pt[0])
        ) * 180 / np.pi

        points_origin_angle = np.where(
            points_origin_angle == 0,
            points_origin_angle, points_origin_angle - offset.angle
        )
        points_origin_angle = np.where(
            points_origin_angle >= 0,
            points_origin_angle, points_origin_angle + 360
        )
        return points_origin_angle

    # 计算模板图像上,该点与其他特征点的旋转角
    first_good_point_sch_origin_angle = get_points_origin_angle(kp_sch_point[:, 0], kp_sch_point[:, 1],
                                                                first_good_point_query)

    # 计算目标图像中,该点与其他特征点的夹角
    kp_sch_rotate_angle = kp_sch_point[:, 2] + first_good_point_angle
    kp_sch_rotate_angle = np.where(kp_sch_rotate_angle >= 360, kp_sch_rotate_angle - 360, kp_sch_rotate_angle)
    kp_sch_rotate_angle = kp_sch_rotate_angle.reshape(kp_sch_rotate_angle.shape + (1,))

    kp_src_angle = kp_src_matches_point[:, :, 2]
    good_point = np.array([matches[index][array[0]] for index, array in
                           enumerate(np.argsort(np.abs(kp_src_angle - kp_sch_rotate_angle)))])

    # 计算各点以first_good_point为原点的旋转角
    good_point_nan = (np.nan, np.nan)
    good_point_pt = np.array([good_point_nan if dMatch is np.nan else (*kp_src[dMatch.trainIdx].pt, )
                             for dMatch in good_point])
    good_point_origin_angle = get_points_origin_angle(good_point_pt[:, 0], good_point_pt[:, 1],
                                                      first_good_point_train)
    threshold = round(5 / 360, 2) * 100
    point_bool = (np.abs(good_point_origin_angle - first_good_point_sch_origin_angle) / 360) * 100 < threshold
    _, index = np.unique(good_point_pt[point_bool], return_index=True, axis=0)
    good = good_point[point_bool]
    good = good[index]
    return good, int(first_good_point_angle), first_good_point
def match_keypoint(des_sch, des_src, k=10):
    """
    特征点匹配

    Args:
        des_src: 待匹配图像的描述符集
        des_sch: 图片模板的描述符集
        k(int): 获取多少匹配点

    Returns:
        List[List[cv2.DMatch]]: 包含最匹配的描述符
    """
    # k=2表示每个特征点取出2个最匹配的对应点
    index_params = {'algorithm': 0, 'tree': 5}
    # 指定递归遍历的次数. 值越高结果越准确，但是消耗的时间也越多
    search_params = {'checks': 50}
    matcher = cv2.FlannBasedMatcher(index_params, search_params)
    matches = matcher.knnMatch(des_sch, des_src, k)
    return matches
def get_keypoint_and_descriptor(image):
    """
    获取图像关键点(keypoint)与描述符(descriptor)
    Args:
        image: 待检测的灰度图像
    Returns:

    """
    sift = cv2.SIFT_create(nfeatures=50000, nOctaveLayers=3, contrastThreshold=0.04,
                                   edgeThreshold=10, sigma=1.6)

    image = np.array(image)
    keypoint, descriptor = sift.detectAndCompute(image=image,mask=None)

    if len(keypoint) < 2:
        return None,None
    return keypoint, descriptor

def find_all_results(im_source, im_search, threshold=0.7, rgb=False, max_count=10, max_iter_counts=20,
                     distance_threshold=150):
    """
    通过特征点匹配,在im_source中找到全部符合im_search的范围
    Args:
        im_source: 待匹配图像
        im_search: 图片模板
        threshold: 识别阈值(0~1)
        rgb: 是否使用rgb通道进行校验
        max_count: 最多可以返回的匹配数量
        max_iter_counts: 最大的搜索次数,需要大于max_count
        distance_threshold: 距离阈值,特征点(first_point)大于该阈值后,不做后续筛选

    Returns:
    """
    result = []

    kp_src, des_src = get_keypoint_and_descriptor(image=im_source)
    kp_sch, des_sch = get_keypoint_and_descriptor(image=im_search)

    if kp_src is None or des_src is None:
        return None

    kp_src, kp_sch = list(kp_src), list(kp_sch)
    # 在特征点集中,匹配最接近的特征点
    matches = np.array(match_keypoint(des_sch=des_sch, des_src=des_src))
    kp_sch_point = np.array([(kp.pt[0], kp.pt[1], kp.angle) for kp in kp_sch])
    kp_src_matches_point = np.array([[(*kp_src[dMatch.trainIdx].pt, kp_src[dMatch.trainIdx].angle)
                                      if dMatch else np.nan for dMatch in match] for match in matches])
    _max_iter_counts = 0
    src_pop_list = []
    while True:
        # 这里没有用matches判断nan, 是因为类型不对
        if (np.count_nonzero(~np.isnan(kp_src_matches_point)) == 0) or (len(result) == max_count) or (
                _max_iter_counts >= max_iter_counts):
            break
        _max_iter_counts += 1
        filtered_good_point, angle, first_point = filter_good_point(matches=matches, kp_src=kp_src,
                                                                         kp_sch=kp_sch,
                                                                         kp_sch_point=kp_sch_point,
                                                                         kp_src_matches_point=kp_src_matches_point)
        if first_point.distance > distance_threshold:
            break

        rect, confidence = None, 0
        try:
            rect, confidence = extract_good_points(im_source=im_source, im_search=im_search, kp_src=kp_src,
                                                        kp_sch=kp_sch, good=filtered_good_point, angle=angle, rgb=rgb)
        except Exception:
            pass
        finally:

            if rect and confidence >= threshold:
                br, tl = (rect[0]+rect[2],rect[1]+rect[3]), (rect[0],rect[1])
                # 移除改范围内的所有特征点 ??有可能因为透视变换的原因，删除了多余的特征点
                for index, match in enumerate(kp_src_matches_point):
                    x, y = match[:, 0], match[:, 1]
                    flag = np.argwhere((x < br[0]) & (x > tl[0]) & (y < br[1]) & (y > tl[1]))
                    for _index in flag:
                        src_pop_list.append(matches[index, _index][0].trainIdx)
                        kp_src_matches_point[index, _index, :] = np.nan
                        matches[index, _index] = np.nan
                result.append(confidence)
            else:
                for match in filtered_good_point:
                    flags = np.argwhere(matches[match.queryIdx, :] == match)
                    for _index in flags:
                        kp_src_matches_point[match.queryIdx, _index, :] = np.nan
                        matches[match.queryIdx, _index] = np.nan

    return result