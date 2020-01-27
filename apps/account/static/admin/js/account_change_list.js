function toWithdraw(url, no){
    var confirm_value = confirm('确认已返利给该用户?');
    if(!confirm_value){
        return false;
    }
    post(url, {no: no},
        function (res) {
            if(res.code === 0){
                alert('提现成功');
                window.location.reload();
            }else{
                alert(res.message);
            }
        },
        function (res) {
            alert(res.message);
        }
    )
}

function toRejectWithdraw(no){
    $('#withdraw-no').val(no);
    $('#reject-withdraw').modal('toggle');
}

function RejectWithdraw(url) {
    var no = $('#withdraw-no').val();
    var remark = $('#reject-remark').val();
    post(url, {no: no, remark: remark},
        function (res) {
            if(res.code === 0){
                alert('已拒绝该用户此次提现');
                window.location.reload();
            }else{
                alert(res.message);
            }
        },
        function (res) {
            alert(res.message);
        }
    )
}