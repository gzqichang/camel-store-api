from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.sms.models import SmsSwitch
from apps.sms.send_sms import send_sms
from apps.utils.send_email import send_email
from apps.utils.disable_for_loaddata import disable_for_loaddata

# Create your models here.


class FeedBack(models.Model):
    user = models.ForeignKey('wxapp.WxUser', verbose_name='用户', null=True, on_delete=models.SET_NULL)
    shop = models.ForeignKey('shop.Shop', verbose_name='所属店铺', on_delete=models.CASCADE)
    goods = models.ForeignKey('goods.Goods', verbose_name='商品', related_name='feedback', null=True, blank=True,
                              on_delete=models.SET_NULL)
    order = models.ForeignKey('trade.Orders', verbose_name='订单', related_name='feedback', null=True, blank=True,
                              on_delete=models.SET_NULL)
    phone = models.CharField(verbose_name='手机号', max_length=20)
    content = models.TextField(verbose_name='反馈内容')
    solve = models.BooleanField(verbose_name='是否解决', default=False)
    update_time = models.DateTimeField(verbose_name='更新时间', auto_now=True)
    add_time = models.DateTimeField(verbose_name='创建时间', auto_now_add=True)

    class Meta:
        verbose_name = verbose_name_plural = '买家反馈'
        ordering = ('solve', '-add_time')


@receiver(post_save, sender=FeedBack)
@disable_for_loaddata
def feedback_save(sender, **kwargs):
    instance = kwargs.get('instance')
    created = kwargs.get('created')
    if created:
        manage = []
        data = {"business": getattr(settings, 'SHOP_NAME'),
                "member": instance.user.nickname,
                "feedbackdetails": instance.content,
                "phonenumber": instance.phone,
                }
        for admin in instance.shop.admin.all():
            if admin.phone and SmsSwitch.get('feedback_notice'):
                send_sms(admin.phone, data, 'SMS_157283313')
            if admin.email:
                manage.append(admin.email)
        if manage:
            subject = '新用户反馈通知'
            text_content = html = f"尊敬的{data.get('business')}商家你好，您小店的客户{data.get('member')}反馈了一条消息，" \
                                  f"反馈消息详情：{data.get('feedbackdetails')}   客户手机号{data.get('phonenumber')}, 可直接联系客户及时回复处理。"
            send_email(subject, text_content, html, manage)


admin = get_user_model()


class FeedbackOperationLog(models.Model):
    admin = models.ForeignKey(admin, verbose_name='操作人', null=True, blank=True, on_delete=models.SET_NULL)
    feedback = models.ForeignKey(FeedBack, related_name='operation_log', null=True, on_delete=models.SET_NULL)
    add_time = models.DateTimeField(verbose_name='操作时间', auto_now_add=True)
    operation = models.CharField(verbose_name='操作', max_length=256)

    class Meta:
        verbose_name = verbose_name_plural = '买家反馈处理日志'
        ordering = ('-add_time', )

    @classmethod
    def create(cls, admin, feedback, operation):
        return cls.objects.create(admin=admin, feedback=feedback, operation=operation)
