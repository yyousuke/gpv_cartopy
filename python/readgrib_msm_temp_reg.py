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
from utils import convert_png2gif
from utils import parse_command
from utils import post
import utils.common

### Start Map Prog ###


def plotmap(sta, lons, lats, uwnd, vwnd, tmp, rh, title, output_filename):
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
        opt_c1 = False  # 1度の等温線を描かない
        opt_barbs = True  # 矢羽を描く
        bstp = 10  # 矢羽を何個飛ばしに描くか
        cstp = 1  # 等値線ラベルを何個飛ばしに付けるか
    else:
        opt_c1 = True  # 1度の等温線を描く
        opt_barbs = True  # 矢羽を描く
        bstp = 2  # 矢羽を何個飛ばしに描くか
        cstp = 3  # 等値線ラベルを何個飛ばしに付けるか

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
    ax.coastlines(color='k', linewidth=1.2)
    #
    # デフォルト：850 hPa気温の等温線を描く
    # 1度の等温線を描く
    if opt_c1:
        # 等温線を描く値のリスト（1Kごと）
        levels_t = np.arange(-90, 61, 1)
        # 等温線を描く
        cr1 = ax.contour(lons,
                         lats,
                         tmp,
                         levels=levels_t,
                         colors='k',
                         linestyles=['-', ':', ':'],
                         linewidths=[1.8, 1.2, 1.2])
        # ラベルを付ける（3Kごと）
        cr1.clabel(cr1.levels[::cstp], fontsize=12, fmt="%d")
    else:
        # 等温線を描く値のリスト（3Kごと）
        levels_t = np.arange(-90, 61, 3)
        # 等温線を描く
        cr2 = ax.contour(lons,
                         lats,
                         tmp,
                         levels=levels_t,
                         colors='k',
                         linestyles='-',
                         linewidths=1.8)
        # ラベルを付ける
        cr2.clabel(cr2.levels[::cstp], fontsize=12, fmt="%d")
    #
    # 色テーブルの設定
    cutils = ColUtils('drywet')  # 色テーブルの選択
    cmap = cutils.get_ctable(under='w')  # 色テーブルの取得
    # 相対湿度の陰影を付ける値をlevelsrにリストとして入れる
    levelsr = [60, 75, 80, 90, 100]
    # 陰影を描く
    cs = ax.contourf(lons, lats, rh, levels=levelsr, cmap=cmap, extend='min')
    # カラーバーを付ける
    cbar = plt.colorbar(cs, orientation='horizontal', shrink=0.9, pad=0.05)
    cbar.set_label('RH (%)')
    #
    # 矢羽を描く
    if opt_barbs:
        ax.barbs(lons[::bstp, ::bstp],
                 lats[::bstp, ::bstp],
                 uwnd[::bstp, ::bstp],
                 vwnd[::bstp, ::bstp],
                 color='r',
                 length=5,
                 linewidth=1.5,
                 sizes=dict(emptybarb=0.01, spacing=0.16, height=0.4))
    #
    #
    # タイトルを付ける
    plt.title(title, fontsize=20)
    # 図を保存
    plt.savefig(output_filename, dpi=300, bbox_inches='tight')
    plt.close()


### End Map Prog ###

if __name__ == '__main__':
    # オプションの読み込み
    args = parse_command(sys.argv, opt_lev=True)
    # 予報時刻, 作図する地域の指定
    fcst_date = args.fcst_date
    sta = args.sta
    file_dir = args.input_dir
    level = args.level
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
        # 指定気圧面の東西風、南北風データを二次元のndarrayで取り出す
        uwnd = msm.ret_var("UGRD_" + str(level) + "mb")  # (m/s)
        vwnd = msm.ret_var("VGRD_" + str(level) + "mb")  # (m/s)
        # 指定気圧面の気温データを二次元のndarrayで取り出す (K->℃)
        tmp = msm.ret_var("TMP_" + str(level) + "mb", offset=-273.15)  # (℃)
        # 指定気圧面の相対湿度データを二次元のndarrayで取り出す ()
        if int(level) >= 300:
            rh = msm.ret_var("RH_" + str(level) + "mb")  # ()
        else:
            rh = np.zeros(tmp.shape)
        # 指定気圧面の相対湿度データを二次元のndarrayで取り出す ()
        # ファイルを閉じる
        msm.close_netcdf()
        #
        # タイトルの設定
        title = str(level) + "hPa " + tlab + " MSM forecast, +" + str(
            fcst_time) + "h (" + tlab_fcst + ")"
        # 出力ファイル名の設定
        hh = "{d:02d}".format(d=fcst_time)
        output_filename = "map_msm_temp_" + str(
            level) + "hPa_" + sta + "_" + str(hh) + ".png"
        # 作図
        plotmap(sta, lons, lats, uwnd, vwnd, tmp, rh, title, output_filename)
        output_filenames.append(output_filename)
    # pngからgifアニメーションに変換
    convert_png2gif(input_filenames=output_filenames,
                    delay="80",
                    output_filename="anim_msm_temp_" + str(level) + "hPa_" +
                    sta + ".gif")
    # 後処理
    post(output_filenames)
