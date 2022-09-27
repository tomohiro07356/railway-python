//monthly_record.htmlにて使用するjavascriptコード

//pythonで出力した配列をHTML経由で受け取り・Parse
let List_N_ID = JSON.parse(document.getElementById("List_N_ID").title);
let List_N_Name = JSON.parse(document.getElementById("List_N_Name").title);
let List_N_PlateA = JSON.parse(document.getElementById("List_N_PlateA").title);
let List_N_PlateB = JSON.parse(document.getElementById("List_N_PlateB").title);
let List_N_PlateC = JSON.parse(document.getElementById("List_N_PlateC").title);
let List_N_PlateD = JSON.parse(document.getElementById("List_N_PlateD").title);
let List_N_Monthly = JSON.parse(document.getElementById("List_N_Monthly").title);
let List_N_Maker = JSON.parse(document.getElementById("List_N_Maker").title);
let List_N_Model = JSON.parse(document.getElementById("List_N_Model").title);
let List_N_Image = JSON.parse(document.getElementById("List_N_Image").title);
let List_Date = JSON.parse(document.getElementById("List_Date").title);
let List_estiPerson = JSON.parse(document.getElementById("List_estiPerson").title);
let List_ImagePath = JSON.parse(document.getElementById("List_ImagePath").title);


//名前選択セレクトボックスの作成
for (let i=0; i<List_N_Name.length; i++){
    if(i===0){
        document.getElementById("name_select").insertAdjacentHTML
        ('beforeend',"<option value='"+i+"' selected>" + List_N_Name[i] + "</option>");
    }
    else{
        document.getElementById("name_select").insertAdjacentHTML
        ('beforeend',"<option value='"+ i +"'>" + List_N_Name[i] + "</option>");
    }
}

//月選択セレクトボックスの作成
let this_month = document.getElementById('month').title;
let this_month_number = Number(this_month);
document.getElementById("month_select").insertAdjacentHTML('beforeend', '<option value="99">全期間表示</option>');
document.getElementById("month_select").insertAdjacentHTML('beforeend', '<option value="2">先々月分</option>' );
document.getElementById("month_select").insertAdjacentHTML('beforeend', '<option value="1">先月分</option>' );
document.getElementById("month_select").insertAdjacentHTML('beforeend', '<option value="0" selected>今月分</option>' ); 

//初期表示
display_information();

//月選択時表示変更
let select_month = document.querySelector('[id="month_select"]');
select_month.onchange = event => {
    display_information();
}

//名前選択時表示変更
let select_name = document.querySelector('[id="name_select"]');
select_name.onchange = event => {
    display_information();
}

//画面表示用関数
function display_information(){
    let {name_num,ym_str} = selected_information_return();
    display_car_img_hist(name_num,ym_str);
    display_comment(name_num,ym_str);
}

// 各ドロップダウンリストで選択されている値を取得する
function selected_information_return(){
    let name_number_str = $("#name_select").val();
    let name_number = Number(name_number_str);
    let date = new Date();
    let year_output_full = date.getFullYear();
    let year_output = String(year_output_full).substr(2);
    let month_output;
    let month_output_str;

    let diff = $("#month_select").val();
    console.log(diff);

    if (diff!=="99"){
        //当日の日付から、month_selectで指定した分だけ月をさかのぼる
        if(date.getMonth() + 1 - diff > 0){
            month_output = date.getMonth() + 1 - diff;
        }else{
            year_output_full = year_output_full - 1;
            year_output = String(year_output_full).substr(2);
            month_output = date.getMonth() + 1 - diff + 12;
        }
        month_output_str = month_output.toString();
        if (month_output_str.length === 1){
            month_output_str = "0" + month_output_str;
        }
    }else{
        //全期間表示の場合
        year_output = "99";
        month_output_str = "99";
    }
    let yearmonth = year_output+month_output_str;
    console.log(yearmonth);
    return {
        name_num: name_number,
        ym_str: yearmonth
    }
}

// 選択された人/年月に対応する車両の写真一覧を表示する
function display_car_img_hist(name_num,ym_str){
    let name = List_N_Name[name_num];
    let img_list = [];
    let date_list = [];
    if (ym_str.substr(0,2) !== "99"){
        //20XX年が選択された場合
        for (let i=0; i<List_estiPerson.length; i++){
            if (List_estiPerson[i] === name){
                if(List_Date[i].substr(0,4) === ym_str){
                    img_list.push(List_ImagePath[i]);
                    date_list.push(List_Date[i]);
                }
            }
        }    
    }
    else{
        //全期間表示の場合
        for (let i=0; i<List_estiPerson.length; i++){
            if (List_estiPerson[i] === name){
                img_list.push(List_ImagePath[i]);
                date_list.push(List_Date[i]);
            }
        }
    }
    // 現在表示されている履歴画像一覧をリセット
    document.getElementById("car_img_hist").innerHTML="";
    //img_listに抽出した画像の表示
    for (let i=0; i<img_list.length; i++){
        let temp_car_img_hist = 
            '<a href="'+ img_list[i] +'?0927a" data-lightbox="histImg" width="185" height="100" class="rounded" data-title="' + date_list[i] +'">'
            +'<img src="'+ img_list[i] + '?0927a" width="200" alt="" style="margin:2px;">'
            +'</a>';
        document.getElementById("car_img_hist").insertAdjacentHTML('beforeend',temp_car_img_hist);
    }
}

// 選択された人の車両情報・参考画像を表示する
function display_comment(name_num,ym_str){
    if (ym_str.substr(0,2) !== "99"){
        //20XX年が選択された場合
        let year_str = "20" + ym_str.substr(0,2);
        let month_str = ym_str.substr(2);
        document.getElementById("top_message").innerHTML = "<h4>" + year_str +"年"+ month_str +"月" + List_N_Name[name_num] +"さんの入庫履歴</h4>";
    }
    else{
        //全期間表示の場合
        document.getElementById("top_message").innerHTML = "<h4>" + List_N_Name[name_num] +"さんの入庫履歴(全期間)</h4>";
    }
    document.getElementById("ID").innerText = "ID: " + List_N_ID[name_num];
    document.getElementById("Plate").innerText = "ナンバー: " + List_N_PlateA[name_num]+List_N_PlateB[name_num]+List_N_PlateC[name_num]+List_N_PlateD[name_num];
    document.getElementById("Monthly").innerText = "月契約：" + List_N_Monthly[name_num];
    document.getElementById("Maker").innerText = "メーカー：" + List_N_Maker[name_num];
    document.getElementById("Model").innerText = "車種：" + List_N_Model[name_num];
    //参考画像の更新
    document.getElementById("Img_tum").src = List_N_Image[name_num] + "?0927a";
    document.getElementById("Img").href = List_N_Image[name_num] + "?0927a";
}


//// 休日指定カレンダー用関数

// document.getElementById("add_holiday").onclick = function() {
//     var AddDate = datepicker.value;
//     document.form_date.add_date.value = AddDate;
// }

// $.get("https://nireco-vehicle-manage.s3-ap-northeast-1.amazonaws.com/NirecoHoliday.json", function(nirecoData) {
//     $.get("https://holidays-jp.github.io/api/v1/date.json", function(holidaysData) {
//         $("#datepicker").datepicker({
//         beforeShowDay: function(date) {
//             if (date.getDay() === 0) {
//                 return [true, 'day-sunday', null];
//             } else if (date.getDay() === 6) {
//                 return [true, 'day-saturday', null];
//             }
//             var holidays = Object.keys(holidaysData);
//             for (var i = 0; i < holidays.length; i++) {
//                 var holiday = new Date(Date.parse(holidays[i]));
//                 if (holiday.getYear() === date.getYear() &&
//                     holiday.getMonth() === date.getMonth() &&
//                     holiday.getDate() === date.getDate()) {
//                     return [true, 'day-holiday', null];
//                 }
//             }
//             var nirecos = Object.keys(nirecoData);
//             for (var i = 0; i < nirecos.length; i++) {
//                 var nireco = new Date(Date.parse(nirecos[i]));
//                 if (nireco.getYear() === date.getYear() &&
//                     nireco.getMonth() === date.getMonth() &&
//                     nireco.getDate() === date.getDate()) {
//                     return [true, 'day-holiday', null];
//                 }
//             }
//             return [true, 'day-weekday', null];
//         }
//         });
//     });
// });

////休日指定用関数ここまで