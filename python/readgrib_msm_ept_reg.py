#!/opt/local/bin/python3
import pandas as pd
import numpy as np
import math
import sys
from datetime import timedelta
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import cartopy.crs as ccrs
from jmaloc import MapRegion
from readgrib import ReadMSM
from utils import ColUtils
from utils import mktheta
from utils import convert_png2gif
from utils import parse_command
from utils import post
import utils.common

### Start Map Prog ###


def plotmap(sta, lons, lats, z50, the85, the50, dthdz, title, output_filename):
    """作図を行う
    
    Parameters:
    ----------
    sta: str
        地点名 
    lons: ndarray
        経度データ（2次元、度）
    lats: ndarray
        緯度データ（2次元、度）
    z50: ndarray
        500hPaジオポテンシャル高度（2次元、m）
    the85: ndarray
        850hPa相当温位（2次元、K）
    the50: ndarray
        500hPa相当温位（2次元、K）
    dthdz: ndarray
       安定度（the50 - the85）（2次元、K）
    title: str
        タイトル
    output_filename: str
        出力ファイル名 
    ----------
    """
    #
    # MapRegion Classの初期化
    region = MapRegion(sta)
    # Map.regionの変数を取得
    lon_step = region.lon_step
    lon_min = region.lon_min
    lon_max = region.lon_max
    lat_step = region.lat_step
    lat_min = region.lat_min
    lat_max = region.lat_max
    if sta == "Japan":
        opt_barbs = True  # 矢羽を描く
        bstp = 10  # 矢羽を何個飛ばしに描くか
        cstp = 5  # 等値線ラベルを何個飛ばしに付けるか
    else:
        opt_barbs = True  # 矢羽を描く
        bstp = 1  # 矢羽を何個飛ばしに描くか
        cstp = 5  # 等値線ラベルを何個飛ばしに付けるか

    # マップを作成
    fig = plt.figure(figsize=(10, 10))
    # cartopy呼び出し
    ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())
    ax.set_extent([lon_min, lon_max, lat_min, lat_max])  # 領域の限定

    # 経度、緯度線を描く
    xticks = np.arange(-180, 180, lon_step)
    yticks = np.arange(-90, 90, lat_step)
    gl = ax.gridlines(crs=ccrs.PlateCarree(),
                      draw_labels=True,
                      linewidth=1,
                      linestyle=':',
                      color='k',
                      alpha=0.8)
    gl.xlocator = mticker.FixedLocator(xticks)  # 経度線
    gl.ylocator = mticker.FixedLocator(yticks)  # 緯度線
    gl.top_labels = False  # 上側の目盛り線ラベルを描かない
    gl.right_labels = False  # 下側の目盛り線ラベルを描かない

    # 海岸線を描く
    ax.coastlines(color='k', linewidth=1.2, zorder=10)
    #
    # 850 hPa等相当温位線
    # 等相当温位線を描く値のリスト
    # 3Kごとに等値線を描く、15Kごとにラベルを付ける
    levels_t = range(210, 390, 3)
    # 等温位線をひく
    cr1 = ax.contour(lons,
                     lats,
                     the85,
                     levels=levels_t,
                     colors='k',
                     linewidths=[1.2, 0.8, 0.8, 0.8, 0.8])
    # ラベルを付ける
    try:
        cr1.clabel(cr1.levels[::cstp], fontsize=12, fmt="%d")  # ラベル
    except Exception as e:
        print(str(e))
    #
    # 500 hPa ジオポテンシャル高度
    # 等高線を描く値のリスト
    # 60mごとに等値線を描く、300mごとにラベルを付ける
    levels_z = range(4800, 6000, 60)
    # 等高線を描く
    cr2 = ax.contour(lons,
                     lats,
                     z50,
                     levels=levels_z,
                     colors='gray',
                     linewidths=[1.2, 0.8, 0.8, 0.8, 0.8])
    # ラベルを付ける
    try:
        cr2.clabel(cr2.levels[::cstp], fontsize=12, fmt="%d")  # ラベル
    except Exception as e:
        print(str(e))
    #
    # 色テーブルの設定
    cutils = ColUtils('haxby')  # 色テーブルの選択
    cmap = cutils.get_ctable(under='purple', over='w')  # 色テーブルの取得
    #
    # dThe/dz
    # 陰影を描く値のリスト
    levels_r = [-9, -6, -3, 0, 3, 6, 9]
    # 陰影を描く
    cs = ax.contourf(lons,
                     lats,
                     dthdz,
                     levels=levels_r,
                     cmap=cmap,
                     extend='both')
    # カラーバーを付ける
    cbar = plt.colorbar(cs, orientation='horizontal', shrink=0.9, pad=0.05)
    cbar.set_label(
        '${\\theta}_e(\mathrm{500 hPa}) - {\\theta}_e(\mathrm{850 hPa})$')
    #
    # タイトルを付ける
    plt.title(title, fontsize=20)
    # 図を保存
    plt.savefig(output_filename, dpi=300, bbox_inches='tight')
    plt.close()


### End Map Prog ###

if __name__ == '__main__':
    pr85 = 85000.0  # pressure (Pa) for 850 hPa
    pr50 = 50000.0  # pressure (Pa) for 500 hPa
    # オプションの読み込み
    args = parse_command(sys.argv)
    # 予報時刻, 作図する地域の指定
    fcst_date = args.fcst_date
    sta = args.sta
    file_dir = args.input_dir
    # 予報時刻からの経過時間（3時間毎に指定可能）
    fcst_end = args.fcst_time
    fcst_str = 0  # 開始時刻
    fcst_step = 3  # 作図する間隔
    # datetimeに変換
    tinfo = pd.to_datetime(fcst_date)
    #
    tsel = tinfo.strftime("%Y%m%d%H%M%S")
    tlab = tinfo.strftime("%m/%d %H UTC")
    #
    # ReadMSM初期化
    msm = ReadMSM(tsel, file_dir, "plev")
    #
    # fcst_timeを変えてplotmapを実行
    output_filenames = []
    for fcst_time in np.arange(fcst_str, fcst_end + 1, fcst_step):
        # fcst_timeを設定
        msm.set_fcst_time(fcst_time)
        # fcst時刻
        tinfo_fcst = tinfo + timedelta(hours=int(fcst_time))
        tlab_fcst = tinfo_fcst.strftime("%m/%d %H UTC")
        # NetCDFデータ読み込み
        lons_1d, lats_1d, lons, lats = msm.readnetcdf()
        # 変数取り出し
        # 850 hPa 気温データを二次元のndarrayで取り出す
        t85 = msm.ret_var("TMP_850mb")  # (K)
        # 500 hPa 気温データを二次元のndarrayで取り出す
        t50 = msm.ret_var("TMP_500mb")  # (K)
        # 850 hPa 相対湿度データを二次元のndarrayで取り出す
        rh85 = msm.ret_var("RH_850mb")  # ()
        # 500 hPa 相対湿度データを二次元のndarrayで取り出す
        rh50 = msm.ret_var("RH_500mb")  # ()
        # 500 hPa ジオポテンシャル高度データを二次元のndarrayで取り出す
        z50 = msm.ret_var("HGT_500mb")  # (m)
        #
        # 850 hPaの相当温位と飽和相当温位を求める
        the85, thes85 = mktheta(pr85, t85, rh85)
        #
        # 500 hPaの相当温位と飽和相当温位を求める
        the50, thes50 = mktheta(pr50, t50, rh50)
        #
        # 500 hPaの飽和相当温位から850 hPaの相当温位を引いて安定度を調べる
        dthdz = the50 - the85
        # ファイルを閉じる
        msm.close_netcdf()
        #
        # タイトルの設定
        title = tlab + " MSM forecast, +" + str(
            fcst_time) + "h (" + tlab_fcst + ")"
        # 出力ファイル名の設定
        hh = "{d:02d}".format(d=fcst_time)
        output_filename = "map_msm_ept_" + sta + "_" + str(hh) + ".png"
        plotmap(sta, lons, lats, z50, the85, the50, dthdz, title,
                output_filename)
        output_filenames.append(output_filename)
    # pngからgifアニメーションに変換
    convert_png2gif(input_filenames=output_filenames,
                    delay="80",
                    output_filename="anim_msm_ept_" + sta + ".gif")
    # 後処理
    post(output_filenames)
