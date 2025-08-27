import numpy as np
import pandas as pd
from typing import List, Tuple, Dict, Any


class TrendlineManager:
    """
    Manager class for handling 3D trendline calculations and visualization.
    """

    def __init__(self):
        self.params = None
        self.color = 'black'  # Default trendline color
        self.polynomial_params = None  # Will store polynomial coefficients
        self.polynomial_color = 'blue'  # Color for polynomial trendline
        self.polynomial_degree = 2  # Default to quadratic polynomial
        
        # Color-filtered trend line parameters
        self.red_params = None
        self.green_params = None
        self.blue_params = None

    def calculate_linear_regression(self, df: pd.DataFrame) -> None:
        """
        Calculate 3D linear regression using the normalized coordinates.
        
        Args:
            df: DataFrame containing 'Xnorm', 'Ynorm', and 'Znorm' columns
        """
        try:
            # Verify we have enough valid points for calculation
            if len(df) < 3:
                raise ValueError(f"Not enough data points for 3D regression. Need at least 3, got {len(df)}.")

            # Filter any remaining NaN values just to be safe
            df_clean = df.dropna(subset=['Xnorm', 'Ynorm', 'Znorm'])
            
            if len(df_clean) < 3:
                raise ValueError(f"After filtering NaNs, not enough valid data points remain. Need at least 3, got {len(df_clean)}.")

            print(f"Calculating linear regression with {len(df_clean)} valid data points")
            
            # Extract normalized coordinates
            x = df_clean['Xnorm'].values
            y = df_clean['Ynorm'].values
            z = df_clean['Znorm'].values
            
            # Create a matrix of x, y coordinates for the independent variables
            A = np.vstack([x, y, np.ones(len(x))]).T
            
            # Check for near-collinearity
            if np.linalg.matrix_rank(A) < min(A.shape):
                print("Warning: Data points are nearly collinear. Using more lenient calculation method.")
            
            # Use a more lenient rcond value (1e-10 instead of None) for better numerical stability
            # params will contain [a, b, c] where z = ax + by + c
            self.params, residuals, rank, s = np.linalg.lstsq(A, z, rcond=1e-10)
            
            print(f"Linear regression successful. Params: {self.params}")
            
        except np.linalg.LinAlgError as e:
            print(f"LinAlgError during regression: {str(e)}")
            # Fall back to a simpler calculation method
            self._fallback_regression(df)
        except Exception as e:
            print(f"Error calculating linear regression: {str(e)}")
            self.params = None
    
    def _fallback_regression(self, df: pd.DataFrame) -> None:
        """
        Simplified fallback method when standard lstsq fails.
        Uses a more robust approach with regularization.
        """
        try:
            print("Using fallback regression method")
            # Filter any NaN values
            df_clean = df.dropna(subset=['Xnorm', 'Ynorm', 'Znorm'])
            
            if len(df_clean) < 2:
                print("Not enough valid points for fallback regression")
                self.params = None
                return
            
            # Extract coordinates
            x = df_clean['Xnorm'].values
            y = df_clean['Ynorm'].values
            z = df_clean['Znorm'].values
            
            # Use a simple regularized approach
            A = np.vstack([x, y, np.ones(len(x))]).T
            
            # Add small regularization term for stability
            ATA = A.T @ A
            reg = np.eye(ATA.shape[0]) * 1e-6  # Small regularization
            ATb = A.T @ z
            
            try:
                # Solve (A^T A + reg) x = A^T b
                self.params = np.linalg.solve(ATA + reg, ATb)
                print(f"Fallback regression successful. Params: {self.params}")
            except:
                # If that fails, use an even simpler average-based approach
                print("Using simplest fallback: average-based line")
                x_mean, y_mean, z_mean = np.mean(x), np.mean(y), np.mean(z)
                # Create simple trendline that passes through mean point
                self.params = np.array([0.001, 0.001, z_mean])
                print(f"Simple average-based params: {self.params}")
        except Exception as e:
            print(f"Error in fallback regression: {str(e)}")
            self.params = None
        
    def get_trendline_points(self, df: pd.DataFrame, num_points: int = 100) -> Dict[str, np.ndarray]:
        """
        Generate points along the calculated trendline.
        
        Args:
            df: DataFrame containing 'Xnorm', 'Ynorm', and 'Znorm' columns
            num_points: Number of points to generate along the trendline
            
        Returns:
            Dictionary containing x, y, z coordinates as numpy arrays for the trendline
        """
        if self.params is None:
            self.calculate_linear_regression(df)
            
        # Get min and max values for x and y
        x_min, x_max = float(df['Xnorm'].min()), float(df['Xnorm'].max())
        y_min, y_max = float(df['Ynorm'].min()), float(df['Ynorm'].max())
        
        # Create evenly spaced points along x and y ranges
        x = np.linspace(x_min, x_max, num_points)
        y = np.linspace(y_min, y_max, num_points)
        
        # Create a grid of points
        X, Y = np.meshgrid(x, y)
        
        # Reshape the arrays to be 1D
        x_points = X.ravel()
        y_points = Y.ravel()
        
        # Calculate z values using the linear equation z = ax + by + c
        z_points = self.params[0] * x_points + self.params[1] * y_points + self.params[2]
        
        return {
            'x': x_points,
            'y': y_points,
            'z': z_points
        }
    
    def get_line_equation(self) -> Tuple[float, float, float]:
        """
        Return the parameters of the line equation.
        
        Returns:
            Tuple containing (a, b, c) for the equation z = ax + by + c
        """
        if self.params is None:
            raise ValueError("Linear regression has not been calculated yet")
        
        return tuple(self.params)
    
    def get_color(self) -> str:
        """
        Return the color of the trendline.
        
        Returns:
            Color string
        """
        return self.color
    
    def set_color(self, color: str) -> None:
        """
        Set the color of the trendline.
        
        Args:
            color: Color string
        """
        self.color = color
    def calculate_polynomial_regression(self, df: pd.DataFrame) -> None:
        """
        Calculate 3D polynomial regression using the normalized coordinates.
        Fits a quadratic surface of the form z = ax² + by² + cxy + dx + ey + f
        
        Args:
            df: DataFrame containing 'Xnorm', 'Ynorm', and 'Znorm' columns
        """
        try:
            # Verify we have enough valid points for calculation
            if len(df) < 6:  # Need at least 6 points for 6 coefficients
                raise ValueError(f"Not enough data points for polynomial regression. Need at least 6, got {len(df)}.")

            # Filter any remaining NaN values
            df_clean = df.dropna(subset=['Xnorm', 'Ynorm', 'Znorm'])
            
            if len(df_clean) < 6:
                raise ValueError(f"After filtering NaNs, not enough valid data points remain. Need at least 6, got {len(df_clean)}.")
            
            print(f"Calculating polynomial regression with {len(df_clean)} valid data points")
            
            # Extract normalized coordinates
            x = df_clean['Xnorm'].values
            y = df_clean['Ynorm'].values
            z = df_clean['Znorm'].values
            
            # Create a design matrix with quadratic terms
            # [x², y², xy, x, y, 1]
            A = np.vstack([
                x**2,           # x²
                y**2,           # y²
                x * y,          # xy (interaction term)
                x,              # x
                y,              # y
                np.ones(len(x)) # constant
            ]).T
            
            # Check for rank deficiency
            if np.linalg.matrix_rank(A) < min(A.shape):
                print("Warning: Design matrix is rank-deficient. Using more lenient calculation method.")
            
            # Use a more lenient rcond value for better numerical stability
            # polynomial_params will contain [a, b, c, d, e, f] where z = ax² + by² + cxy + dx + ey + f
            self.polynomial_params, residuals, rank, s = np.linalg.lstsq(A, z, rcond=1e-10)
            
            print(f"Polynomial regression successful. Params: {self.polynomial_params}")
            
        except np.linalg.LinAlgError as e:
            print(f"LinAlgError during polynomial regression: {str(e)}")
            # Fall back to linear regression if polynomial fails
            self._fallback_polynomial_regression(df)
        except Exception as e:
            print(f"Error calculating polynomial regression: {str(e)}")
            self.polynomial_params = None
    
    def _fallback_polynomial_regression(self, df: pd.DataFrame) -> None:
        """
        Simplified fallback method when standard polynomial regression fails.
        Uses a simpler model or added regularization.
        """
        try:
            print("Using fallback polynomial regression method")
            # Filter any NaN values
            df_clean = df.dropna(subset=['Xnorm', 'Ynorm', 'Znorm'])
            
            if len(df_clean) < 4:  # Need at least 4 points for a simpler model
                print("Not enough valid points for fallback polynomial regression")
                self.polynomial_params = None
                return
                
            # Extract coordinates
            x = df_clean['Xnorm'].values
            y = df_clean['Ynorm'].values
            z = df_clean['Znorm'].values
            
            # Try a simpler model with fewer terms (just linear with an intercept)
            A = np.vstack([x, y, np.ones(len(x))]).T
            
            try:
                # Try linear least squares with high regularization
                ATA = A.T @ A
                reg = np.eye(ATA.shape[0]) * 1e-4  # Stronger regularization
                ATb = A.T @ z
                
                # Solve (A^T A + reg) x = A^T b for linear coefficients
                linear_params = np.linalg.solve(ATA + reg, ATb)
                
                # Create simplified polynomial parameters [0, 0, 0, d, e, f]
                # Zero out the quadratic terms
                self.polynomial_params = np.array([0.0, 0.0, 0.0, linear_params[0], linear_params[1], linear_params[2]])
                print(f"Fallback to simpler polynomial model successful: {self.polynomial_params}")
            except:
                # Last resort: create a flat surface at mean z height
                z_mean = np.mean(z)
                self.polynomial_params = np.array([0.0, 0.0, 0.0, 0.0, 0.0, z_mean])
                print(f"Using flat surface at mean z-height: {z_mean}")
        except Exception as e:
            print(f"Error in fallback polynomial regression: {str(e)}")
            self.polynomial_params = None
    
    def get_polynomial_color(self) -> str:
        """
        Return the color of the polynomial trendline.
        
        Returns:
            Color string
        """
        return self.polynomial_color
    
    def set_polynomial_color(self, color: str) -> None:
        """
        Set the color of the polynomial trendline.
        
        Args:
            color: Color string
        """
        self.polynomial_color = color
        
    def get_polynomial_points(self, df: pd.DataFrame, num_points: int = 100) -> Dict[str, np.ndarray]:
        """
        Generate points for the polynomial surface.
        
        Args:
            df: DataFrame containing 'Xnorm', 'Ynorm', and 'Znorm' columns
            num_points: Number of points to generate along each axis
            
        Returns:
            Dictionary containing x, y, z coordinates as 2D numpy arrays for the polynomial surface
        """
        if self.polynomial_params is None:
            self.calculate_polynomial_regression(df)
            
        # Get min and max values for x and y
        x_min, x_max = float(df['Xnorm'].min()), float(df['Xnorm'].max())
        y_min, y_max = float(df['Ynorm'].min()), float(df['Ynorm'].max())
        
        # Create evenly spaced points along x and y ranges
        x = np.linspace(x_min, x_max, num_points)
        y = np.linspace(y_min, y_max, num_points)
        
        # Create a grid of points - keep as 2D arrays for wireframe plotting
        X, Y = np.meshgrid(x, y)
        
        # Calculate z values directly on the 2D grid using the polynomial equation
        # z = ax² + by² + cxy + dx + ey + f where polynomial_params = [a, b, c, d, e, f]
        a, b, c, d, e, f = self.polynomial_params
        Z = (
            a * X**2 +          # ax²
            b * Y**2 +          # by²
            c * X * Y +         # cxy
            d * X +             # dx
            e * Y +             # ey
            f                   # f
        )
        
        return {
            'x': X,
            'y': Y,
            'z': Z
        }
    
    def get_polynomial_equation(self) -> Tuple[float, float, float, float, float, float]:
        """
        Return the parameters of the polynomial equation.
        
        Returns:
            Tuple containing (a, b, c, d, e, f) for the equation z = ax² + by² + cxy + dx + ey + f
        """
        if self.polynomial_params is None:
            raise ValueError("Polynomial regression has not been calculated yet")
        
        return tuple(self.polynomial_params)
    
    def calculate_color_filtered_regression(self, df: pd.DataFrame, color: str) -> None:
        """
        Calculate 3D linear regression for points of a specific color.
        
        Args:
            df: DataFrame containing 'Xnorm', 'Ynorm', 'Znorm', and 'Color' columns
            color: Color to filter by ('red', 'green', 'blue')
        """
        try:
            # Filter data by color (case-insensitive)
            color_df = df[df['Color'].str.lower() == color.lower()].copy()
            
            if len(color_df) < 3:
                print(f"Not enough {color} data points for regression. Need at least 3, got {len(color_df)}.")
                self._set_color_params(color, None)
                return
            
            # Filter any remaining NaN values
            df_clean = color_df.dropna(subset=['Xnorm', 'Ynorm', 'Znorm'])
            
            if len(df_clean) < 3:
                print(f"After filtering NaNs, not enough valid {color} data points remain. Need at least 3, got {len(df_clean)}.")
                self._set_color_params(color, None)
                return
            
            print(f"Calculating {color} linear regression with {len(df_clean)} valid data points")
            
            # Extract normalized coordinates
            x = df_clean['Xnorm'].values
            y = df_clean['Ynorm'].values
            z = df_clean['Znorm'].values
            
            # Create a matrix of x, y coordinates for the independent variables
            A = np.vstack([x, y, np.ones(len(x))]).T
            
            # Check for near-collinearity
            if np.linalg.matrix_rank(A) < min(A.shape):
                print(f"Warning: {color} data points are nearly collinear. Using more lenient calculation method.")
            
            # Use a more lenient rcond value for better numerical stability
            # params will contain [a, b, c] where z = ax + by + c
            params, residuals, rank, s = np.linalg.lstsq(A, z, rcond=1e-10)
            
            self._set_color_params(color, params)
            print(f"{color.capitalize()} linear regression successful. Params: {params}")
            
        except np.linalg.LinAlgError as e:
            print(f"LinAlgError during {color} regression: {str(e)}")
            self._fallback_color_regression(df, color)
        except Exception as e:
            print(f"Error calculating {color} linear regression: {str(e)}")
            self._set_color_params(color, None)
    
    def _fallback_color_regression(self, df: pd.DataFrame, color: str) -> None:
        """
        Simplified fallback method for color-filtered regression when standard lstsq fails.
        """
        try:
            print(f"Using fallback {color} regression method")
            # Filter data by color
            color_df = df[df['Color'].str.lower() == color.lower()].copy()
            df_clean = color_df.dropna(subset=['Xnorm', 'Ynorm', 'Znorm'])
            
            if len(df_clean) < 2:
                print(f"Not enough valid {color} points for fallback regression")
                self._set_color_params(color, None)
                return
            
            # Extract coordinates
            x = df_clean['Xnorm'].values
            y = df_clean['Ynorm'].values
            z = df_clean['Znorm'].values
            
            # Use a simple regularized approach
            A = np.vstack([x, y, np.ones(len(x))]).T
            
            # Add small regularization term for stability
            ATA = A.T @ A
            reg = np.eye(ATA.shape[0]) * 1e-6
            ATb = A.T @ z
            
            try:
                # Solve (A^T A + reg) x = A^T b
                params = np.linalg.solve(ATA + reg, ATb)
                self._set_color_params(color, params)
                print(f"Fallback {color} regression successful. Params: {params}")
            except:
                # If that fails, use an even simpler average-based approach
                print(f"Using simplest {color} fallback: average-based line")
                x_mean, y_mean, z_mean = np.mean(x), np.mean(y), np.mean(z)
                params = np.array([0.001, 0.001, z_mean])
                self._set_color_params(color, params)
                print(f"Simple {color} average-based params: {params}")
        except Exception as e:
            print(f"Error in {color} fallback regression: {str(e)}")
            self._set_color_params(color, None)
    
    def _set_color_params(self, color: str, params) -> None:
        """
        Set the parameters for a specific color trend line.
        
        Args:
            color: Color name ('red', 'green', 'blue')
            params: Parameters array or None
        """
        color_lower = color.lower()
        if color_lower == 'red':
            self.red_params = params
        elif color_lower == 'green':
            self.green_params = params
        elif color_lower == 'blue':
            self.blue_params = params
    
    def _get_color_params(self, color: str):
        """
        Get the parameters for a specific color trend line.
        
        Args:
            color: Color name ('red', 'green', 'blue')
            
        Returns:
            Parameters array or None
        """
        color_lower = color.lower()
        if color_lower == 'red':
            return self.red_params
        elif color_lower == 'green':
            return self.green_params
        elif color_lower == 'blue':
            return self.blue_params
        return None
    
    def get_color_trendline_points(self, df: pd.DataFrame, color: str, num_points: int = 100) -> Dict[str, np.ndarray]:
        """
        Generate points along the calculated color-filtered trendline.
        
        Args:
            df: DataFrame containing 'Xnorm', 'Ynorm', 'Znorm', and 'Color' columns
            color: Color to generate trend line for ('red', 'green', 'blue')
            num_points: Number of points to generate along the trendline
            
        Returns:
            Dictionary containing x, y, z coordinates as numpy arrays for the trendline,
            or None if no valid trend line exists for this color
        """
        params = self._get_color_params(color)
        
        if params is None:
            # Try to calculate if not already done
            self.calculate_color_filtered_regression(df, color)
            params = self._get_color_params(color)
            
        if params is None:
            return None
            
        # Filter data by color to get appropriate ranges
        color_df = df[df['Color'].str.lower() == color.lower()].copy()
        df_clean = color_df.dropna(subset=['Xnorm', 'Ynorm', 'Znorm'])
        
        if len(df_clean) == 0:
            return None
            
        # Get min and max values for x and y from color-filtered data
        x_min, x_max = float(df_clean['Xnorm'].min()), float(df_clean['Xnorm'].max())
        y_min, y_max = float(df_clean['Ynorm'].min()), float(df_clean['Ynorm'].max())
        
        # Create evenly spaced points along x and y ranges
        x = np.linspace(x_min, x_max, num_points)
        y = np.linspace(y_min, y_max, num_points)
        
        # Create a grid of points
        X, Y = np.meshgrid(x, y)
        
        # Reshape the arrays to be 1D
        x_points = X.ravel()
        y_points = Y.ravel()
        
        # Calculate z values using the linear equation z = ax + by + c
        z_points = params[0] * x_points + params[1] * y_points + params[2]
        
        return {
            'x': x_points,
            'y': y_points,
            'z': z_points
        }
    
    def get_color_line_equation(self, color: str) -> Tuple[float, float, float]:
        """
        Return the parameters of the color-filtered line equation.
        
        Args:
            color: Color name ('red', 'green', 'blue')
            
        Returns:
            Tuple containing (a, b, c) for the equation z = ax + by + c,
            or None if no valid equation exists for this color
        """
        params = self._get_color_params(color)
        if params is None:
            return None
        return tuple(params)
