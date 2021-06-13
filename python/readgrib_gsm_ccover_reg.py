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
from utils import val2col
from utils import convert_png2gif
from utils import parse_command
from utils import post
import utils.common


### Start Map Prog ###


def plotmap(fcst_time, sta, lons_1d, lats_1d, lons, lats, mslp, cfrl, cfrm,
            cfrh, title, output_filename):
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
        opt_c1 = True     # 1hPaの等圧線を描く
        cstp = 1          # 等値線ラベルを何個飛ばしに付けるか

    # マップを作成
    fig = plt.figure(figsize=(10, 10))
    # cartopy呼び出し
    #ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())
    ax = fig.add_axes((0.1, 0.3, 0.8, 0.6), projection=ccrs.PlateCarree())
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
    # 雲量の陰影を付ける値をlevelsrにリストとして入れる
    levelsc = np.arange(0, 100.1, 5)
    # 色テーブル取得
    cmapl = plt.get_cmap('Reds')  # 下層
    cmapm = plt.get_cmap('Greens')  # 中層
    cmaph = plt.get_cmap('Blues')  # 上層
    # 陰影を描く（下層雲）
    csl = ax.contourf(lons, lats, cfrl, levels=levelsc, cmap=cmapl, alpha=0.3)
    # 陰影を描く（中層雲）
    csm = ax.contourf(lons, lats, cfrm, levels=levelsc, cmap=cmapm, alpha=0.3)
    # 陰影を描く（上層雲）
    csh = ax.contourf(lons, lats, cfrh, levels=levelsc, cmap=cmaph, alpha=0.3)
    #
    # タイトルを付ける
    plt.title(title, fontsize=20)
    #
    # val2colクラスの初期化（気温の範囲はtmin、tmaxで設定、tstepで刻み幅）
    cbarh = val2col(cmap='Blues', tmin=0., tmax=100.1, tstep=20.)
    cbarm = val2col(cmap='Greens', tmin=0., tmax=100.1, tstep=20.)
    cbarl = val2col(cmap='Reds', tmin=0., tmax=100.1, tstep=20.)
    # カラーバーを付ける
    cbarh.colorbar(fig, anchor=(0.35, 0.26), size=(0.3, 0.02), label=False)
    cbarm.colorbar(fig, anchor=(0.35, 0.225), size=(0.3, 0.02), label=False)
    cbarl.colorbar(fig, anchor=(0.35, 0.19), size=(0.3, 0.02), label=True)
    # ラベルを付ける
    cbarh.clabel(fig,
                 anchor=(0.34, 0.26),
                 size=(0.1, 0.02),
                 text="High cloud cover")
    cbarm.clabel(fig,
                 anchor=(0.34, 0.225),
                 size=(0.1, 0.02),
                 text="Middle cloud cover")
    cbarl.clabel(fig,
                 anchor=(0.34, 0.19),
                 size=(0.1, 0.02),
                 text="Low cloud cover")
    #
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
    fcst_step = 1 # 作図する間隔
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
        # 海面更生気圧を二次元のndarrayで取り出す
        mslp = gsm.ret_var("PRMSL_meansealevel", fact=0.01)  # (hPa)
        # 下層雲量を二次元のndarrayで取り出す
        cfrl = gsm.ret_var("LCDC_surface")  # ()
        # 中層雲量を二次元のndarrayで取り出す
        cfrm = gsm.ret_var("MCDC_surface")  # ()
        # 上層雲量を二次元のndarrayで取り出す
        cfrh = gsm.ret_var("HCDC_surface")  # ()
        # ファイルを閉じる
        gsm.close_netcdf()
        #
        # タイトルの設定
        title = tlab + " GSM forecast, +" + str(
            fcst_time) + "h (" + tlab_fcst + ")"
        # 出力ファイル名の設定
        hh = "{d:02d}".format(d=fcst_time)
        output_filename = "map_gsm_ccover_" + sta + "_" + str(hh) + ".png"
        plotmap(fcst_time, sta, lons_1d, lats_1d, lons, lats, mslp, cfrl, cfrm,
                cfrh, title, output_filename)
        output_filenames.append(output_filename)
    # pngからgifアニメーションに変換
    convert_png2gif(input_filenames=output_filenames,
                    delay="80",
                    output_filename="anim_gsm_ccover_" + sta + ".gif")
    # 後処理
    post(output_filenames)
