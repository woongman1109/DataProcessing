/*
Parameters:
    TD1,TD2,Yb,A1,A2,Tau1,Tau2
*/

/* Function file
[General Information]
Function Name = ExpAssocDelay2
Brief Description = Biphasic exponential association with plateau before exponential begins.
Function Source = fgroup.ExpAssocDelay2
Number Of Parameters = 7
Function Type = Built-in
Function Form = Equations
Number Of Independent Variables = 1
Number Of Dependent Variables = 1

[Fitting Parameters]
Names = TD1,TD2,Yb,A1,A2,Tau1,Tau2
Initial Values = 1(V),2(V),0(V),1(V),1(V),1(V),1(V)
Meanings = 1st time offset: x value at which 1st exponential begins,2nd time offset: x value at which 2nd exponential begins,Baseline: y value before exponential begins,1st amplitude: change in response for 1st exponential,2nd amplitude: change in response for 2nd exponential,1st time constant,2nd time constant
Lower Bounds = --(I, Off),--(I, Off),--(I, Off),--(I, Off),--(I, Off),--(I, Off),--(I, Off)
Upper Bounds = --(I, Off),--(I, Off),--(I, Off),--(I, Off),--(I, Off),--(I, Off),--(I, Off)
Naming Method = User-Defined


[Independent Variables]
x = 


[Dependent Variables]
y = 


[Formula]

if (x < TD1)
	y = Yb;
else if (x < TD2)
	y = Yb + A1 * (1 - exp(-(x - TD1)/Tau1));
else
	y = Yb + A1 * (1 - exp(-(x - TD1)/Tau1)) + A2 * (1 - exp(-(x - TD2)/Tau2));


[Initializations]


[After Fitting]


[Controls]
General Linear Constraints = 0
Initialization Scripts = 0
Scripts After Fitting = 0

[Parameters Initialization]
TD1 = min(x_data);
TD2 = min(x_data);

int sign;
double temp;
temp = get_exponent_cuv(x_y_curve, &Yb, &A1, &sign);

int nSize = x_data.GetSize();

Yb = y_data[0] + y_data[nSize-1] - Yb;

if (temp > 0)
{
	A1 = sign * exp(A1 + temp*(x_data[0] + x_data[nSize-1]) - TD1*temp);
	Tau1 = 1 / temp;
}
else
{
	A1 = -sign * exp(A1 - TD1/temp);
	Tau1 = -1 / temp;
}

// Some cases, exp(A) above can be 0 or overflow.
// This ensures A gets initialized to decent value if that happens.
A1 = ((0/0 == A1) || (0 == A1) ? abs(y_data[nSize-1]) - abs(y_data[0]) : A1);

A1 = A2 = A1 / 2;
Tau1 = Tau2 = Tau1 / 2;


[Derived Parameter Settings]
Names = k1,k2
Meanings = 1st rate constant,2nd rate constant

[Constants]


[Constraints]


[Derived Parameters]
k1 = 1/Tau1
k2 = 1/Tau2


[LaTeX Formula]
\[ y =
  \begin{cases}
    Y_{b}\quad &(x<TD_{1})\\
    Y_{b}+A_{1}\left(1-e^{-\frac{(x-TD_{1})}{\tau_{1}}}\right)\quad &(TD_{1}\leq x<TD_{2})\\
    Y_{b}+A_{1}\left(1-e^{-\frac{(x-TD_{1})}{\tau_{1}}}\right)+A_{2}\left(1-e^{-\frac{(x-TD_{2})}{\tau_{2}}}\right)\quad &(x\geq TD_{2})\\ 
  \end{cases}
\]
*/

/*   Parameters Initialization   */
TD1 = min(x_data);
TD2 = min(x_data);

int sign;
double temp;
temp = get_exponent_cuv(x_y_curve, &Yb, &A1, &sign);

int nSize = x_data.GetSize();

Yb = y_data[0] + y_data[nSize-1] - Yb;

if (temp > 0)
{
	A1 = sign * exp(A1 + temp*(x_data[0] + x_data[nSize-1]) - TD1*temp);
	Tau1 = 1 / temp;
}
else
{
	A1 = -sign * exp(A1 - TD1/temp);
	Tau1 = -1 / temp;
}

// Some cases, exp(A) above can be 0 or overflow.
// This ensures A gets initialized to decent value if that happens.
A1 = ((0/0 == A1) || (0 == A1) ? abs(y_data[nSize-1]) - abs(y_data[0]) : A1);

A1 = A2 = A1 / 2;
Tau1 = Tau2 = Tau1 / 2;



/*      Function    */
if (x < TD1)
	y = Yb;
else if (x < TD2)
	y = Yb + A1 * (1 - exp(-(x - TD1)/Tau1));
else
	y = Yb + A1 * (1 - exp(-(x - TD1)/Tau1)) + A2 * (1 - exp(-(x - TD2)/Tau2));



/*  Derived Parameters  */
k1=1/Tau1
k2=1/Tau2



% Biphasic exponential function
biphasic_exp = @(p, t) p(1) * (1 - exp(-p(2) * t)) + p(3) * (1 - exp(-p(4) * t));

% Sample data (replace these with your actual data)
t_data = [0, 1, 2, 3, 4, 5];  % Time points
y_data = [0, 1.2, 2.1, 2.8, 3.2, 3.4];  % Observed values

% Initial guess for the parameters [A1, k1, A2, k2]
p0 = [1, 0.1, 1, 0.05];

% Fit the curve
options = optimset('Display','off');
p_opt = lsqcurvefit(biphasic_exp, p0, t_data, y_data, [], [], options);

% Optimal parameters
A1 = p_opt(1);
k1 = p_opt(2);
A2 = p_opt(3);
k2 = p_opt(4);
fprintf('Optimal parameters: A1=%.4f, k1=%.4f, A2=%.4f, k2=%.4f\n', A1, k1, A2, k2);

% Plot the data and the fitted curve
t_fit = linspace(0, 5, 100);
y_fit = biphasic_exp(p_opt, t_fit);

figure;
scatter(t_data, y_data, 'filled');
hold on;
plot(t_fit, y_fit, 'r-');
xlabel('Time');
ylabel('Y');
legend('Data', 'Fitted curve');
hold off;
