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
from readgrib import ReadGSM
from utils import ColUtils
from utils import convert_png2gif
from utils import convert_png2mp4
from utils import parse_command
from utils import post
import utils.common

### Start Map Prog ###


def plotmap(fcst_time, sta, lons, lats, tmp, rain, title, output_filename):
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
        opt_c1 = False  # 1Kの等温線を描かない
        cstp = 1  # 等値線ラベルを何個飛ばしに付けるか
    else:
        opt_c1 = True  # 1hPaの等圧線を描く
        cstp = 2  # 等値線ラベルを何個飛ばしに付けるか

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
    cmap = plt.get_cmap('seismic')  # 色テーブルの選択
    if opt_c1:
        # 等温線をひく間隔(1Kごと)をlevelsにリストとして入れる
        levels1 = range(math.floor(tmp.min() - math.fmod(tmp.min(), 2)),
                        math.ceil(tmp.max()) + 1, 1)
        # 等温線をひく
        cr1 = ax.contour(lons,
                         lats,
                         tmp,
                         levels=levels1,
                         linestyles=['-', ':'],
                         cmap=cmap,
                         linewidths=0.8)
        # ラベルを付ける
        cr1.clabel(cr1.levels[::cstp], fontsize=12, fmt="%d")
    else:
        # 等温線をひく間隔(2Kごと)をlevelsにリストとして入れる
        levels2 = range(math.floor(tmp.min() - math.fmod(tmp.min(), 2)),
                        math.ceil(tmp.max()) + 1, 2)
        # 等温線をひく
        cr2 = ax.contour(lons,
                         lats,
                         tmp,
                         levels=levels2,
                         cmap=cmap,
                         linewidths=0.8)
        # ラベルを付ける
        cr2.clabel(cr2.levels[::cstp], fontsize=12, fmt="%d")
    #
    #
    cutils = ColUtils('s3pcpn_l')  # 色テーブルの選択
    cmap = cutils.get_ctable(under='gray', over='brown')  # 色テーブルの取得
    # 降水量の陰影を付ける値をlevelsrにリストとして入れる
    levelsr = [0.2, 1, 5, 10, 20, 50, 80, 100]
    # 陰影を描く
    cs = ax.contourf(lons,
                     lats,
                     rain,
                     levels=levelsr,
                     cmap=cmap,
                     extend='both')
    # カラーバーを付ける
    cbar = plt.colorbar(cs, orientation='horizontal', shrink=0.9, pad=0.05)
    cbar.set_label('precipitation (mm/hr)')
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
    args = parse_command(sys.argv)
    # 予報時刻, 作図する地域の指定
    fcst_date = args.fcst_date
    sta = args.sta
    file_dir = args.input_dir
    # 予報時刻からの経過時間（１時間毎に指定可能）
    fcst_end = args.fcst_time
    fcst_str = 0  # 開始時刻
    fcst_step = 1  # 作図する間隔
    # datetimeに変換
    tinfo = pd.to_datetime(fcst_date)
    #
    tsel = tinfo.strftime("%Y%m%d%H%M%S")
    tlab = tinfo.strftime("%m/%d %H UTC")
    #
    # ReadGSM初期化
    gsm = ReadGSM(tsel, file_dir, "surf")
    #
    # fcst_timeを変えてplotmapを実行
    output_filenames = []
    for fcst_time in np.arange(fcst_str, fcst_end + 1, fcst_step):
        # fcst_timeを設定
        gsm.set_fcst_time(fcst_time)
        # fcst時刻
        tinfo_fcst = tinfo + timedelta(hours=int(fcst_time))
        tlab_fcst = tinfo_fcst.strftime("%m/%d %H UTC")
        # NetCDFデータ読み込み
        lons_1d, lats_1d, lons, lats = gsm.readnetcdf()
        # 変数取り出し
        # 降水量を二次元のndarrayで取り出す
        rain = gsm.ret_var("APCP_surface")  # (mm/h)
        # 気温を二次元のndarrayで取り出す (K->℃)
        tmp = gsm.ret_var("TMP_2maboveground", offset=-273.15)  # (℃)
        # ファイルを閉じる
        gsm.close_netcdf()
        #
        # タイトルの設定
        title = tlab + " GSM forecast, +" + str(
            fcst_time) + "h (" + tlab_fcst + ")"
        # 出力ファイル名の設定
        hh = "{d:02d}".format(d=fcst_time)
        output_filename = "map_gsm_stemp_" + sta + "_" + str(hh) + ".png"
        # 作図
        plotmap(fcst_time, sta, lons, lats, tmp, rain, title, output_filename)
        output_filenames.append(output_filename)
    # pngからgifアニメーションに変換
    convert_png2gif(input_filenames=output_filenames,
                    delay="80",
                    output_filename="anim_gsm_stemp_" + sta + ".gif")
    # pngからmp4アニメーションに変換
    convert_png2mp4(input_file="map_gsm_stemp_" + sta + "_%02d.png",
                    output_filename="anim_gsm_stemp_" + sta + ".mp4")
    # 後処理
    post(output_filenames)
