import time
import os
import numpy as np
import struct
from PIL import Image
import xml.etree.cElementTree as ET
from pathlib import Path

# 全局变量
recorder_path = r'C:\\recorders'
lotID_Target = ['BT0845.0036']
file_name_list = []
rec_list = []
finish_list = []
last_checked_time = time.time()
last_checked_time_rec = time.time()
last_checked_time_rec_latest = last_checked_time

def get_file_path(recorder_path, last_checked_time_rec):
    new_folder_path = []
    r = os.walk(recorder_path)
    for path, dir_list, file_list in r:
        if len(dir_list) > 0:
            for folder in dir_list:
                p = Path(path)
                if os.path.basename(p) == 'recorder':
                    new_folder_path = os.path.join(recorder_path, folder)
                    file_mod_time = os.path.getmtime(os.path.join(recorder_path, folder))
                    if file_mod_time > last_checked_time_rec - 5000 and folder not in rec_list and folder != [1]:
                        print(folder)
                        rec_list.append(folder)
                        print(rec_list)
                        new_folder_path = os.path.join(recorder_path, folder)
                        last_checked_time_rec_latest = file_mod_time
                        return new_folder_path
                    else:
                        new_folder_path = None
        else:
            continue
    return new_folder_path

def copy_old_files(result_path, path):
    Device_ID = []
    Step_ID = []
    offset_x = 0
    offset_y = 0
    flag = 0
    TestID = []
    ScanMode = []
    Scan_Mode = []
    TestID_former = 0
    
    try:
        r = os.walk(path)
        for path, dir_list, file_list in r:
            for file_name in file_list:
                if os.path.splitext(file_name)[-1] == '.xml':
                    path_abs = os.path.abspath(file_name)
                    tree = ET.ElementTree(file=os.path.join(path, file_name))
                    root = tree.getroot()
                    Device_ID = root.find('.RecipeInfo').attrib['DeviceId']
                    Step_ID = root.find('.RecipeInfo').attrib['StepId']
                    print(Device_ID + " " + Step_ID)
                    GDS_INFO = root.find('.GDSRecipe/GDSXML').text
                    offset = GDS_INFO[1:80].split('"')[1]
                    offset_x = float(offset.split("'")[0])
                    offset_y = float(offset.split("'")[1])
                    for child_of_root in root:
                        if child_of_root.tag == 'Tests':
                            for elem in child_of_root:
                                TestID.append(elem.get('Id'))
                                for param in elem:
                                    if param.tag == 'ImageParam':
                                        for mode in param:
                                            if mode.tag == 'AdvScanningControl':
                                                M1 = mode.get('EnableQuadScan')
                                                M2 = mode.get('EnableReverseScan')
                                                if M1 == 'True':
                                                    ScanMode.append("1")
                                                elif M2 == 'True':
                                                    ScanMode.append("2")
                                                else:
                                                    ScanMode.append("3")
                    
                    print(ScanMode)
                    print(TestID)
                    recorder_name = path.split("\\")[-1]
                    print(recorder_name)
                    LotID = recorder_name.split("-")[-4].split("-")[0]
                    Port_SlotID = recorder_name.split("-")[-1]
                    SlotID = recorder_name.split("-")[-2]
                    print(LotID + ' ' + Port_SlotID + ' ' + SlotID)
                    dist = result_path + recorder_name
                    os.makedirs(dist, exist_ok=True)
                    
    except Exception as e:
        flag = 1
        print('flag=' + str(flag))
        print('No D2DB info')
        print(e)
    
    return Device_ID, Step_ID, offset_x, offset_y, flag, last_checked_time, ScanMode, TestID

def copy_new_files(result_path, path, Device_ID, Step_ID, offset_x, offset_y, last_checked_time, Scan_Mode, Test_ID):
    global count
    count = 0
    ID = 0
    ScanMode = 0
    TestID_former = 0
    current_time = time.time()
    path = str(path)
    print(path)
    recorder_name = path.split("\\")[-1]
    LotID = str(recorder_name).split("-")[-3].split("-")[0]
    Port_SlotID = str(recorder_name).split("-")[-1]
    SlotID = str(recorder_name).split("-")[-2]
    
    r = os.walk(path)
    for path, dir_list, file_list in r:
        for file_name in file_list:
            if os.path.splitext(file_name)[-1] == '.raw':
                file_mod_time = os.path.getmtime(os.path.join(path, file_name))
                if file_mod_time > last_checked_time:
                    with open(os.path.join(path, file_name), 'rb') as img_read:
                        x = img_read.read()
                        scan_width, = struct.unpack('i', x[0:4])
                        Start = scan_width ** 2 + 32768
                        gl_x = Start + 52*4
                        if len(x) > gl_x:
                            test_ID, = struct.unpack('i', x[gl_x:-4:gl_x])
                            Total = Start + 52 * 4 + 4070 * 4
                            if len(x) >= Total:
                                image_id, = struct.unpack('i', x[20:24])
                                die_id_X, = struct.unpack('i', x[84:88])
                                die_id_Y, = struct.unpack('i', x[88:92])
                                Scan_dir, = struct.unpack('i', x[92:96])
                                Img_GDSPosX, = struct.unpack('i', x[192:196])
                                Img_GDSPosY, = struct.unpack('i', x[196:200])
                                PointID, = struct.unpack('i', x[200:204])
                                wafer_PosX, = struct.unpack('f', x[56:60])
                                wafer_PosY, = struct.unpack('f', x[60:64])
                                
                                if test_ID != TestID_former:
                                    for i in range(len(Test_ID)):
                                        if Test_ID[i] == str(test_ID):
                                            ID = i
                                            Scan_Mode = ScanMode[ID-1] if ID-1 < len(ScanMode) else "0"
                                            TestID_former = test_ID
                                    print(Scan_dir)
                                    print(Scan_Mode)
                                
                                # 读取图像数据

                                img_data_start = 32768  # 图像数据起始位置
                                img_data = x[img_data_start:img_data_start + scan_width * scan_width]
                                
                                # 根据数据类型转换
                                if len(img_data) >= scan_width * scan_width:
                                    # 假设图像数据是8位灰度
                                    raw_array = np.frombuffer(img_data, dtype=np.uint8).reshape((scan_width, scan_width))
                                    
                                    # 根据扫描方向处理图像
                                    if Scan_dir == 0 or Scan_dir == 1:
                                        raw_image = np.flipud(np.rot90(raw_array, -1))
                                    elif Scan_dir == 2 or Scan_dir == 3:
                                        raw_image = np.flipud(np.rot90(raw_array, 1))
                                    else:
                                        raw_image = raw_array
                                    
                                    # 生成文件名
                                    file_name_list = Device_ID + '_' + Step_ID + '_' + LotID + '_' + \\
                                        str(image_id) + '_' + str(die_id_X) + '_' + str(die_id_Y) + '_' + \\
                                        str(PointID) + '_' + str(Img_GDSPosX) + '_' + str(Img_GDSPosY) + '_' + \\
                                        str(round(wafer_PosX, 6)) + '_' + str(round(wafer_PosY, 6)) + '_' + \\
                                        str(round((Img_GDSPosX - offset_x)/1000000, 6)) + '_' + \\
                                        str(round((Img_GDSPosY - offset_y)/1000000, 6)) + '.bmp'
                                    
                                    # 保存图像
                                    im = Image.fromarray(raw_image)
                                    save_path = os.path.join(result_path, recorder_name, file_name_list)
                                    os.makedirs(os.path.dirname(save_path), exist_ok=True)
                                    im.save(save_path)
                                    print(file_name_list)
                                    count = count + 1
                        else:
                            break
    
    last_checked_time = current_time
    return count, last_checked_time

def schedule_task():
    cycle = 0
    flag = 0
    count = 0
    result_path = 'X:/AMTD-EP5/Auto_raw_to_bmp/'
    while cycle < 10000:
        path = get_file_path(recorder_path, last_checked_time_rec_latest)
        time.sleep(300)
        cycle = cycle + 1
        print(cycle)
        print(path)
        if path is not None:
            recorder_name = path.split("\\")[-1]
            if "." in recorder_name:
                ID_front = recorder_name.split(".")[0].split("-")[-1]
                ID_behind = recorder_name.split(".")[1].split("-")[0]
                LotID = ID_front + "." + ID_behind
                print(LotID)
            else:
                LotID = recorder_name.split(".")[2]
            
            if recorder_name not in finish_list and LotID in lotID_Target and flag == 0:
                Device_ID, Step_ID, offset_x, offset_y, flag, last_checked_time, Scan_Mode, Test_ID = copy_old_files(result_path, path)
                while True:
                    print("sleep")
                    time.sleep(1000)
                    print('flag=' + str(flag))
                    if flag == 0:
                        count, last_checked_time = copy_new_files(result_path, path, Device_ID, Step_ID, 
                                                                  offset_x, offset_y, last_checked_time, 
                                                                  Scan_Mode, Test_ID)
                        print(count)
                        if count == 0:
                            print("Searching for new rec")
                            finish_list.append(path.split("\\")[-1])
                            break
                        else:
                            continue
                    else:
                        continue
            else:
                continue
        else:
            continue

if __name__ == '__main__':
    schedule_task()