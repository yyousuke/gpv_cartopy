#!/opt/local/bin/python3
import pandas as pd
import numpy as np
import math
import sys
from datetime import timedelta
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import cartopy.crs as ccrs
from jmaloc import MapRegion
from readgrib import ReadMSM
from utils import ColUtils
from utils import convert_png2gif
from utils import convert_png2mp4
from utils import parse_command
from utils import post
import utils.common


### Start Map Prog ###


def plotmap(sta, lons, lats, mslp, rain, title, output_filename):
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
        opt_c1 = False    # 1hPaの等圧線を描かない
        cstp = 2          # 等値線ラベルを何個飛ばしに付けるか
    else:
        opt_c1 = False    # 1hPaの等圧線を描かない
        cstp = 1          # 等値線ラベルを何個飛ばしに付けるか

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
    if opt_c1:
        # 等圧線をひく間隔(1hPaごと)をlevelsにリストとして入れる
        levels1 = range(math.floor(mslp.min() - math.fmod(mslp.min(), 1)),
                        math.ceil(mslp.max()) + 1, 1)
        # 等圧線をひく
        cr1 = ax.contour(lons,
                         lats,
                         mslp,
                         levels=levels1,
                         colors='k',
                         linestyles=':',
                         linewidths=1.2)
        # ラベルを付ける
        cr1.clabel(cr1.levels[::cstp * 2], fontsize=12, fmt="%d")
    # 等圧線をひく間隔(2hPaごと)をlevelsにリストとして入れる
    levels2 = range(math.floor(mslp.min() - math.fmod(mslp.min(), 2)),
                    math.ceil(mslp.max()) + 1, 2)
    # 等圧線をひく
    cr2 = ax.contour(lons,
                     lats,
                     mslp,
                     levels=levels2,
                     colors='k',
                     linewidths=1.2)
    # ラベルを付ける
    cr2.clabel(cr2.levels[::cstp], fontsize=12, fmt="%d")
    #
    #
    cutils = ColUtils('wysiwyg')  # 色テーブルの選択
    cmap = cutils.get_ctable(under='gray', over='r')  # 色テーブルの取得
    # 降水量の陰影を付ける値をlevelsrにリストとして入れる
    levelsr = [1, 5, 10, 20, 50, 80, 100, 200, 400, 600]
    # 陰影を描く
    cs = ax.contourf(lons,
                     lats,
                     rain,
                     levels=levelsr,
                     cmap=cmap,
                     extend='both')
    # カラーバーを付ける
    cbar = plt.colorbar(cs, orientation='horizontal', shrink=0.9, pad=0.05)
    cbar.set_label('precipitation (mm)')
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
    # 予報時刻からの経過時間
    fcst_end = args.fcst_time
    # datetimeに変換
    tinfo = pd.to_datetime(fcst_date)
    #
    tsel = tinfo.strftime("%Y%m%d%H%M%S")
    tlab = tinfo.strftime("%m/%d %H UTC")
    #
    # ReadMSM初期化
    msm = ReadMSM(tsel, file_dir, "surf")
    #
    # fcst_timeを変えてplotmapを実行
    rain_add = []
    output_filenames = []
    for fcst_time in np.arange(0, fcst_end + 1, 1):
        # fcst_timeを設定
        msm.set_fcst_time(fcst_time)
        # NetCDFデータ読み込み
        lons_1d, lats_1d, lons, lats = msm.readnetcdf()
        # 変数取り出し
        # 海面更生気圧を二次元のndarrayで取り出す
        mslp = msm.ret_var("PRMSL_meansealevel", fact=0.01)  # (hPa)
        # 降水量を二次元のndarrayで取り出す
        rain = msm.ret_var("APCP_surface")  # (mm/h)
        rain_add.append(rain)
        # ファイルを閉じる
        msm.close_netcdf()
    #
    nt = len(rain_add)
    rain_add = np.vstack(rain_add).reshape(nt, lons.shape[0], lons.shape[1])
    print(rain_add.shape)
    rain = rain_add.sum(axis=0)
    # タイトルの設定
    title = tlab + " MSM forecast, +" + "0-" + str(fcst_time) + "h rain & +"  + str(fcst_time) + "h SLP"
    # 出力ファイル名の設定
    output_filename = "map_msm_rain_sum" + "0-" + str(fcst_time) + "_" + sta + ".png"
    # 作図
    plotmap(sta, lons, lats, mslp, rain, title, output_filename)
