from django import forms
from .models import BoolConfig, Level, Version


class BoolConfigForm(forms.ModelForm):

    content = forms.ChoiceField(label='配置设置', choices=(('true', '是'), ('false', '否')))

    class Meta:
        model = BoolConfig
        fields = ('label', 'content', )


class LevelForm(forms.ModelForm):
    class Meta:
        model = Level
        fields = ('title', 'threshold', 'discount', 'icon')

    def clean_discount(self):
        discount = self.cleaned_data['discount']
        if discount < 0 or discount > 100:
            raise forms.ValidationError('折扣设置错误，请输入0~100的数值')
        return self.cleaned_data['discount']


class VersionForm(forms.ModelForm):
    content = forms.CharField(label='版本号')

    class Meta:
        model = BoolConfig
        fields = ('label', 'content', )


class StoreTypeForm(forms.ModelForm):
    content = forms.ChoiceField(
        label='店铺类型',
        choices=(('camel', '骆驼小店'), ('cloud', '齐昌云店')),
    )

    class Meta:
        model = BoolConfig
        fields = ('label', 'content', )