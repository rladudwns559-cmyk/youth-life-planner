"""매월 초 정액 납입·고정 단리·세전만 지원하는 순수 계산."""
from dataclasses import dataclass
from decimal import Context,Decimal,ROUND_HALF_UP,localcontext

MAX_PAYMENT=1_000_000_000_000
MAX_TERM_MONTHS=120
METHOD='MONTHLY_BEGINNING_FIXED_SIMPLE_PRETAX'

class SavingsValidationError(ValueError):
    def __init__(self,code:str,field:str):
        self.code=code;self.field=field
        super().__init__(f'{code}: {field}')

def validate_rate(rate:Decimal)->None:
    if type(rate) is not Decimal or not rate.is_finite():
        raise SavingsValidationError('INVALID_DECIMAL_RATE','annual_base_rate_percent')
    if rate<0 or rate>100 or rate.as_tuple().exponent < -4:
        raise SavingsValidationError('INVALID_RATE_RANGE_OR_SCALE','annual_base_rate_percent')

@dataclass(frozen=True,slots=True)
class RecurringSavingsInput:
    monthly_payment:int
    term_months:int
    annual_base_rate_percent:Decimal
    calculation_method:str=METHOD

    def __post_init__(self):
        if type(self.monthly_payment) is not int or not 0<=self.monthly_payment<=MAX_PAYMENT:
            raise SavingsValidationError('INVALID_MONTHLY_PAYMENT','monthly_payment')
        if type(self.term_months) is not int or not 1<=self.term_months<=MAX_TERM_MONTHS:
            raise SavingsValidationError('INVALID_TERM_MONTHS','term_months')
        validate_rate(self.annual_base_rate_percent)
        if self.calculation_method!=METHOD:
            raise SavingsValidationError('UNSUPPORTED_ASSUMPTION','calculation_method')

@dataclass(frozen=True,slots=True)
class RecurringSavingsResult:
    monthly_payment:int
    term_months:int
    annual_base_rate_percent:str
    annual_rate_ratio:str
    total_principal_krw:int
    estimated_interest_before_tax_krw:int
    estimated_maturity_before_tax_krw:int
    unrounded_interest_krw:str

    def to_dict(self):
        from dataclasses import asdict
        return asdict(self)

def calculate_recurring_savings(data:RecurringSavingsInput)->RecurringSavingsResult:
    if type(data) is not RecurringSavingsInput:
        raise SavingsValidationError('INVALID_SAVINGS_INPUT_TYPE','savings_input')
    # 호출자의 Decimal 정밀도/반올림/trap 설정으로 결과가 달라지지 않게 한다.
    with localcontext(Context(prec=50,rounding=ROUND_HALF_UP)):
        rate=data.annual_base_rate_percent/Decimal(100)
        principal=data.monthly_payment*data.term_months
        interest=Decimal(data.monthly_payment)*rate*data.term_months*(data.term_months+1)/Decimal(24)
        rounded=int(interest.quantize(Decimal('1'),rounding=ROUND_HALF_UP))
        return RecurringSavingsResult(data.monthly_payment,data.term_months,
            format(data.annual_base_rate_percent.normalize(),'f'),format(rate.normalize(),'f'),
            principal,rounded,principal+rounded,format(interest,'f'))
