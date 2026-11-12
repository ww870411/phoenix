


var selectedValue_path;

document.addEventListener("DOMContentLoaded", function () {
    // 在这里放置你的 JavaScript 代码
    if (selectedValue_path) {
        window.location.href = selectedValue_path; // 在当前窗口中打开链接
    }
});

$("#selectpath").change(function () {
    // selectedValue_path = $(this).val();
    selectedValue_path = this.value;
    // console.log('selectedValue_path:', selectedValue_path);

    if (selectedValue_path) {
        window.location.href = selectedValue_path; // 在当前窗口中打开链接
    }
});



function gk_get_data() {   // 接收sz_selected作为参数
    $.ajax({
        url: "/gk_get_data/",
        // data: { 'sz_selected': sz_selected },   //data是以表单形式编码的数据，前端用request.form.get()获取
        type: 'POST',
        dataType: 'json',   //这句，要求flask返回的值必须是json格式
        success: function (data) {

            console.log("data['yw2_dict']", data['yw2_dict']);

            // 遍历 首站参数区表格 每一行，更新匹配行的内容
            var table1 = $('#sorting1').DataTable();
            $('#tbody1 tr').each(function () {

                var rowIndex = $(this).index();
                var cellIndex = 2;
                // var column = table1.fnSettings().aoColumns[cellIndex];
                var stationName = table1.fnGetData(rowIndex, cellIndex);
                console.log('stationName：', stationName, rowIndex);

                var cellIndex = 3;
                // var column = table1.fnSettings().aoColumns[cellIndex];
                var dictType = table1.fnGetData(rowIndex, cellIndex);
                // console.log('dictType：', dictType);


                if (data[dictType] && data[dictType][stationName]) {
                    rowData = data[dictType][stationName];
                } else {
                    // 处理属性不存在的逻辑
                    rowData = null
                }
                console.log('rowData：', rowData);
                if (rowData) {
                    // 更新表格对应行的内容
                    // console.log('rowData.WENDU, rowData.YALI, rowData.LIULIANG, rowData.RELIANG：', rowData.WENDU, rowData.YALI, rowData.LIULIANG, rowData.RELIANG);
                    $(this).find('td:eq(2)').text(rowData.WENDU !== null ? rowData.WENDU : '');
                    $(this).find('td:eq(3)').text(rowData.YALI !== null ? rowData.YALI : '');
                    $(this).find('td:eq(4)').text(rowData.LIULIANG !== null ? rowData.LIULIANG : '');
                    // 下面是北海水炉#2-#3在流量列显示负荷
                    if (rowIndex >= 23 && rowIndex <= 25) {
                        $(this).find('td:eq(5)').text(rowData.RELIANG !== null ? rowData.FUHE : '');
                    }
                    else {
                        $(this).find('td:eq(5)').text(rowData.RELIANG !== null ? rowData.RELIANG : '');
                    }
                } else {
                    $(this).find('td:eq(2)').text('');
                    $(this).find('td:eq(3)').text('');
                    $(this).find('td:eq(4)').text('');
                    $(this).find('td:eq(5)').text('');
                }
            });





            // 遍历 电厂参数区 每一行，更新匹配行的内容
            var table2 = $('#sorting2').DataTable();
            $('#tbody2 tr').each(function () {

                var rowIndex = $(this).index();
                var cellIndex = 2;
                // var column = table1.fnSettings().aoColumns[cellIndex];
                var stationName = table2.fnGetData(rowIndex, cellIndex);
                // console.log('stationName：', stationName);

                var cellIndex = 3;
                // var column = table1.fnSettings().aoColumns[cellIndex];
                var dictType = table2.fnGetData(rowIndex, cellIndex);
                // console.log('dictType：', dictType);


                if (data[dictType] && data[dictType][stationName]) {
                    rowData = data[dictType][stationName];
                } else {
                    // 处理属性不存在的逻辑
                    rowData = null
                }
                // console.log('rowData：', rowData);
                if (rowData) {
                    // 更新表格对应行的内容
                    // console.log('rowData.WENDU, rowData.YALI, rowData.LIULIANG, rowData.RELIANG：', rowData.WENDU, rowData.YALI, rowData.LIULIANG, rowData.RELIANG);
                    $(this).find('td:eq(2)').text(rowData.WENDU !== null ? rowData.WENDU : '');
                    $(this).find('td:eq(3)').text(rowData.YALI !== null ? rowData.YALI : '');
                    $(this).find('td:eq(4)').text(rowData.LIULIANG !== null ? rowData.LIULIANG : '');
                    $(this).find('td:eq(5)').text(rowData.RELIANG !== null ? rowData.RELIANG : '');
                } else {
                    $(this).find('td:eq(2)').text('');
                    $(this).find('td:eq(3)').text('');
                    $(this).find('td:eq(4)').text('');
                    $(this).find('td:eq(5)').text('');
                }
            });





            // 遍历 一网参数区 每一行，更新匹配行的内容
            var table3 = $('#sorting3').DataTable();
            $('#tbody3 tr').each(function () {

                var rowIndex = $(this).index();
                var cellIndex = 2;
                // var column = table3.fnSettings().aoColumns[cellIndex];
                var stationName = table3.fnGetData(rowIndex, cellIndex);
                // console.log('一网，表3，stationName：', stationName);

                var cellIndex = 3;
                // var column = table3.fnSettings().aoColumns[cellIndex];
                var dictType = table3.fnGetData(rowIndex, cellIndex);
                // console.log('一网，表3，dictType：', dictType);


                if (data[dictType] && data[dictType][stationName]) {
                    rowData = data[dictType][stationName];
                } else {
                    // 处理属性不存在的逻辑
                    rowData = null
                }
                // console.log('一网，表3，rowData：', rowData);
                if (rowData) {
                    // 更新表格对应行的内容
                    // console.log('rowData.WENDU, rowData.YALI, rowData.LIULIANG, rowData.RELIANG：', rowData.WENDU, rowData.YALI, rowData.LIULIANG, rowData.RELIANG);
                    $(this).find('td:eq(2)').text(rowData.WENDU !== null ? rowData.WENDU : '');
                    $(this).find('td:eq(3)').text(rowData.YALI !== null ? rowData.YALI : '');
                    $(this).find('td:eq(4)').text(rowData.LIULIANG !== null ? rowData.LIULIANG : '');
                    $(this).find('td:eq(5)').text(rowData.RELIANG !== null ? rowData.RELIANG : '');
                } else {
                    $(this).find('td:eq(2)').text('');
                    $(this).find('td:eq(3)').text('');
                    $(this).find('td:eq(4)').text('');
                    $(this).find('td:eq(5)').text('');
                }
            });





            // 遍历 换热站及商户参数区 每一行，更新匹配行的内容
            var table4 = $('#sorting4').DataTable();
            $('#tbody4 tr').each(function () {

                var rowIndex = $(this).index();
                var cellIndex = 2;
                // var column = table4.fnSettings().aoColumns[cellIndex];
                var stationName = table4.fnGetData(rowIndex, cellIndex);
                // console.log('stationName：', stationName);

                var cellIndex = 3;
                // var column = table4.fnSettings().aoColumns[cellIndex];
                var dictType = table4.fnGetData(rowIndex, cellIndex);
                // console.log('dictType：', dictType);


                if (data[dictType] && data[dictType][stationName]) {
                    rowData = data[dictType][stationName];
                } else {
                    // 处理属性不存在的逻辑
                    rowData = null
                }
                // console.log('rowData：', rowData);
                if (rowData) {
                    // 更新表格对应行的内容
                    // console.log('rowData.WENDU, rowData.YALI, rowData.LIULIANG, rowData.RELIANG：', rowData.WENDU, rowData.YALI, rowData.LIULIANG, rowData.RELIANG);
                    $(this).find('td:eq(2)').text(rowData.WENDU !== null ? rowData.WENDU : '');
                    $(this).find('td:eq(3)').text(rowData.YALI !== null ? rowData.YALI : '');
                    $(this).find('td:eq(4)').text(rowData.LIULIANG !== null ? rowData.LIULIANG : '');
                    $(this).find('td:eq(5)').text(rowData.RELIANG !== null ? rowData.RELIANG : '');
                } else {
                    $(this).find('td:eq(2)').text('');
                    $(this).find('td:eq(3)').text('');
                    $(this).find('td:eq(4)').text('');
                    $(this).find('td:eq(5)').text('');
                }
            });





        },
        error: function (xhr, status, error) {
            // console.log('函数设置首站时间字符串颜色为红');
            // $("#datetime_sz").css("color", "red");
            console.error('发生错误：' + error);
            $.modal.alert('查首站数据，请求出现错误：' + error);
        }
    });
}







// 使用定时函数每30秒调用一次set_sz_data函数
setInterval(function () {
    gk_get_data();   // 查询工况数据
}, 15000);




// function applyCustomStyles() {
//     // 修改表头背景颜色
//     $('table.dataTable thead th').css('background-color', '#136cab');

//     // 修改表头字体颜色
//     $('table.dataTable thead th').css('color', '#333');
//   }


$(document).ready(function () {


    // 下面是设置缩放后的字体
    var whei = $(window).width()
    $(".custom").css({ fontSize: whei / 130 + 1 + "px" })


    $(window).resize(function () {
        var whei = $(window).width()
        $(".custom").css({ fontSize: whei / 130 + 1 + "px" })
    });





    // 监听窗口大小变化
    $(window).resize(function () {
    });




    var table1 = $('#sorting1').DataTable({
        "bPaginate": false, // 禁用分页
        "bFilter": false, // 禁用搜索框
        "bInfo": false, // 禁用表格信息
        "bSort": false, // 禁用排序
        "bAutoWidth": false // 禁用自动列宽
    });

    // 隐藏第3、4、5列
    table1.fnSetColumnVis(2, false);
    table1.fnSetColumnVis(3, false);
    table1.fnSetColumnVis(4, false);




    var table2 = $('#sorting2').DataTable({
        "bPaginate": false, // 禁用分页
        "bFilter": false, // 禁用搜索框
        "bInfo": false, // 禁用表格信息
        "bSort": false, // 禁用排序
        "bAutoWidth": false // 禁用自动列宽
    });

    // 隐藏第3、4列
    table2.fnSetColumnVis(2, false);
    table2.fnSetColumnVis(3, false);
    table2.fnSetColumnVis(4, false);




    var table3 = $('#sorting3').DataTable({
        "bPaginate": false, // 禁用分页
        "bFilter": false, // 禁用搜索框
        "bInfo": false, // 禁用表格信息
        "bSort": false, // 禁用排序
        "bAutoWidth": false // 禁用自动列宽
    });

    // 隐藏第3、4、5列
    table3.fnSetColumnVis(2, false);
    table3.fnSetColumnVis(3, false);
    table3.fnSetColumnVis(4, false);




    var table4 = $('#sorting4').DataTable({
        "bPaginate": false, // 禁用分页
        "bFilter": false, // 禁用搜索框
        "bInfo": false, // 禁用表格信息
        "bSort": false, // 禁用排序
        "bAutoWidth": false // 禁用自动列宽
    });

    // 隐藏第3、4列
    table4.fnSetColumnVis(2, false);
    table4.fnSetColumnVis(3, false);
    table4.fnSetColumnVis(4, false);

});