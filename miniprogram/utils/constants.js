// utils/constants.js
const MEMBERSHIP_CONFIG = {
  free: {
    name: '普通用户',
    monthlyLimit: 10,
    desc: '每月可查看10条启事'
  },
  member: {
    name: '会员',
    monthlyLimit: 30,
    desc: '每月可查看30条启事',
    price: 99,
    priceLabel: '99元/年'
  },
  vip: {
    name: '大会员',
    monthlyLimit: 999,
    desc: '每月可查看999条启事',
    price: 999,
    priceLabel: '999元/年'
  }
};

const GENDER_OPTIONS = ['男', '女'];

const INCOME_OPTIONS = [
  '3万以下', '3-5万', '5-10万', '10-20万',
  '20-30万', '30-50万', '50万以上'
];

const HEIGHT_OPTIONS = [
  '150cm以下', '150-155cm', '155-160cm', '160-165cm',
  '165-170cm', '170-175cm', '175-180cm', '180-185cm',
  '185-190cm', '190cm以上'
];

const FIELD_LABELS = {
  phone: '手机号码',
  name: '姓名',
  nickname: '昵称',
  gender: '性别',
  age: '年龄',
  birthday: '生日',
  socialAccount: '社交账号',
  occupation: '职业',
  income: '收入',
  isPublicSector: '是否体制内',
  height: '身高',
  weight: '体重'
};

const REQUIRED_FIELDS = ['phone', 'name', 'gender', 'age'];
const OPTIONAL_FIELDS = ['nickname', 'socialAccount', 'occupation', 'income', 'isPublicSector', 'height', 'weight'];

module.exports = {
  MEMBERSHIP_CONFIG,
  GENDER_OPTIONS,
  INCOME_OPTIONS,
  HEIGHT_OPTIONS,
  FIELD_LABELS,
  REQUIRED_FIELDS,
  OPTIONAL_FIELDS
};
