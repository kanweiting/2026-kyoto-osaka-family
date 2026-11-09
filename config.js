// 部署設定：記帳要多人同步的話，把 Google Apps Script Web App 網址貼在這裡（見 README）。
// 留空 = 只存在自己的瀏覽器裡（適合先試用）。
window.TRIP_CONFIG = {
  sheetApi: '',   // 五人同步的 Apps Script /exec 網址；new_trip.py 會依 setup.json 填入
  tripFile: 'data/trip.json',
  placesFile: 'data/places.json',
  areasFile: 'data/areas.json'
};
