/******************************************
 *  Base Function
 ******************************************/
/**
 *   Cookie 读取
 */
function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = jQuery.trim(cookies[i]);
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

/**
 * LocalStorage 的读取和包装, 使用 JSON 进行转换
 */

function setStorage(key, value) {
    localStorage.setItem(key, JSON.stringify(value))
}

function getStorage(key, value) {
    return JSON.parse(localStorage.getItem(key));
}

function clearStorage() {
    localStorage.clear();
}
/**
 *  请求的函数
 */
function post(url, data, success, error, complete) {
    $.ajax({
        url: url,
        type: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
        },
        data: data,
        success: function(res){
            if(typeof success !== 'undefined'){
                success(res);
            }
        },
        error: function (res) {
            if(typeof error !== 'undefined'){
                error(res.responseJSON);
            }
        },
        complete: function (res, status) {
            if(typeof complete !== 'undefined'){
                complete(res);
            }
        }
    });
}

/**
 *  控制元素的显示与隐藏
 */
function toggleDisplay(e) {
    var that = $(e);
    if (that.is(':hidden')) {
        that.show();
    }
    else {
        that.hide();
    }
}
/**
 *  遮罩的显示与隐藏
 */
function toggleModal(e) {
    var that = $(e);
    var isHidden = that.is(':hidden');

    if(isHidden){
        $('body').addClass('modal-open');
        that.show();
    }else{
        $('body').removeClass('modal-open');
        that.hide();
    }
}

/**
 *  监测金额的输入
 */
function inputAmount(input) {
    var that = $(input);
    var reg = that.val().match(/\d+\.?\d{0,2}/);
    var txt = '';
    if (reg !== null) {
        txt = reg[0];
    }
    that.val(txt);
}