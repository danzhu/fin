> start [ALPHA] ID
> start _ UNDERSCORE
> start 0 ZERO
> start 123456789 NUM
> start + PLUS
> start - MINUS
> start * MULTIPLIES
> start / DIVIDES
> start % MODULUS
> start = ASSN
> start & AMP
> start ! EXCL
> start : COLON
> start ( LPAREN
> start ) RPAREN
> start [ LBRACKET
> start ] RBRACKET
> start { LBRACE
> start } RBRACE
> start < LT
> start > GT
> start \ BACKSLASH
> start . DOT
> start , COMMA
> start ; SEMICOLON
> start [SPACE] start
> start # comment
> ID [ALPHA][NUM]_ ID
> UNDERSCORE [ALPHA][NUM]_ ID
> MINUS 0 neg_zero
> MINUS 123456789 NUM
> MINUS > ARROW
> ZERO . FLOAT
> neg_zero . FLOAT
> NUM . FLOAT
> NUM [NUM] NUM
> FLOAT [NUM] FLOAT
> PLUS = PLUS_ASSN
> MINUS = MINUS_ASSN
> MULTIPLIES = MULTIPLIES_ASSN
> DIVIDES = DIVIDES_ASSN
> MODULUS = MODULUS_ASSN
> ASSN > ARM
> ASSN = EQ
> EXCL = NE
> LT = LE
> GT = GE
> comment [ANY] comment
> comment [LF] start
type ZERO NUM
type PLUS_ASSN INC_ASSN
type MINUS_ASSN INC_ASSN
type MULTIPLIES_ASSN INC_ASSN
type DIVIDES_ASSN INC_ASSN
type MODULUS_ASSN INC_ASSN
type EQ COMP
type NE COMP
type GT COMP
type GE COMP
type LT COMP
type LE COMP
keyword import IMPORT
keyword struct STRUCT
keyword enum ENUM
keyword def DEF
keyword let LET
keyword if IF
keyword then THEN
keyword else ELSE
keyword match MATCH
keyword begin BEGIN
keyword while WHILE
keyword do DO
keyword break BREAK
keyword continue CONTINUE
keyword redo REDO
keyword return RETURN
keyword and AND
keyword or OR
keyword not NOT
